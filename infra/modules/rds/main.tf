locals {
  name = lower(var.project_name)
}

# DB subnet group spans both dedicated data-tier subnets (one per AZ).
#
# NOTE: the group is given a new name (-data) so moving the DB from the app
# subnets to the data subnets creates a NEW group rather than mutating the
# in-use one — AWS forbids ModifyDBSubnetGroup that removes subnets a running
# instance occupies. create_before_destroy sequences it as: build the data
# group -> relocate/replace the instances onto it -> drop the old app group.
resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db-subnet-data"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.project_name}-db-subnet-data"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# RDS security group. Ingress on the DB port added once the ECS task SG
# exists (least privilege) — no rules now, so nothing can reach the DB yet.
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "RDS Postgres (port ${var.port}) from ECS tasks only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# Self-ingress on the DB port so the read replica can stream from the primary
# (both share this SG). Without it replication silently fails to sync.
resource "aws_security_group_rule" "rds_self_replication" {
  type              = "ingress"
  from_port         = var.port
  to_port           = var.port
  protocol          = "tcp"
  security_group_id = aws_security_group.rds.id
  self              = true
  description       = "Primary/replica replication"
}

# Primary instance. Free-tier friendly: db.t3.micro, 20GB gp2, single-AZ.
# Pinned to the first AZ (AZ-a).
resource "aws_db_instance" "primary" {
  identifier        = "${local.name}-db"
  engine            = "postgres"
  engine_version    = var.engine_version
  instance_class    = var.instance_class
  availability_zone = var.availability_zones[0]
  port              = var.port

  allocated_storage = var.allocated_storage
  storage_type      = "gp2"

  # Encryption at rest using the default aws/rds KMS key (no extra cost).
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  multi_az            = false
  publicly_accessible = false

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Daily automated snapshots to S3 (RDS-managed), kept 7 days then expired.
  backup_retention_period = var.backup_retention_period

  skip_final_snapshot = true
  deletion_protection = false

  # The live password is the source of truth (the app reads it via the frozen
  # DATABASE_URL secret). var.db_password only seeds the instance at creation;
  # ignore it afterwards so plan never drifts/resets the password.
  #
  # replace_triggered_by: when the subnet group is replaced (app -> data tier),
  # RECREATE the instance instead of letting the provider attempt an in-place
  # ModifyDBInstance subnet-group move. AWS forbids moving a DB that has a read
  # replica, so a destroy+create (born in the data subnets) is the only path.
  lifecycle {
    ignore_changes       = [password]
    replace_triggered_by = [aws_db_subnet_group.this.id]
  }

  tags = {
    Name = "${var.project_name}-db"
  }
}

# Read replica pinned to the second AZ (AZ-b) so a single-AZ outage never
# takes both down. Same region -> inherits storage, creds, encryption from
# the source. NOT free tier (a second instance).
resource "aws_db_instance" "replica" {
  count = var.create_read_replica ? 1 : 0

  identifier          = "${local.name}-db-replica"
  replicate_source_db = aws_db_instance.primary.identifier
  instance_class      = var.instance_class
  availability_zone   = var.availability_zones[1]

  multi_az            = false
  publicly_accessible = false

  # Same-region replica inherits encryption from the source. Declare it to
  # match the API value, else Terraform reads true vs unset(null) and forces
  # replacement on every plan.
  storage_encrypted = true

  vpc_security_group_ids = [aws_security_group.rds.id]

  skip_final_snapshot = true

  # Recreate (not in-place move) when the subnet group is replaced, and so the
  # replica is torn down before the primary is recreated — RDS can't move a
  # primary that still has a replica attached.
  lifecycle {
    replace_triggered_by = [aws_db_subnet_group.this.id]
  }

  tags = {
    Name = "${var.project_name}-db-replica"
  }
}
