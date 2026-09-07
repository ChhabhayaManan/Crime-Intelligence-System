locals {
  name = lower(var.project_name)
}

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

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "RDS Postgres (port ${var.port}) from ECS tasks only"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

resource "aws_security_group_rule" "rds_self_replication" {
  type              = "ingress"
  from_port         = var.port
  to_port           = var.port
  protocol          = "tcp"
  security_group_id = aws_security_group.rds.id
  self              = true
  description       = "Primary/replica replication"
}

resource "aws_db_instance" "primary" {
  identifier        = "${local.name}-db"
  engine            = "postgres"
  engine_version    = var.engine_version
  instance_class    = var.instance_class
  availability_zone = var.availability_zones[0]
  port              = var.port

  allocated_storage = var.allocated_storage
  storage_type      = "gp2"

  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  multi_az            = false
  publicly_accessible = false

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = var.backup_retention_period

  skip_final_snapshot = true
  deletion_protection = false

  lifecycle {
    ignore_changes       = [password]
    replace_triggered_by = [aws_db_subnet_group.this.id]
  }

  tags = {
    Name = "${var.project_name}-db"
  }
}

resource "aws_db_instance" "replica" {
  count = var.create_read_replica ? 1 : 0

  identifier          = "${local.name}-db-replica"
  replicate_source_db = aws_db_instance.primary.identifier
  instance_class      = var.instance_class
  availability_zone   = var.availability_zones[1]

  multi_az            = false
  publicly_accessible = false

  storage_encrypted = true

  vpc_security_group_ids = [aws_security_group.rds.id]

  skip_final_snapshot = true

  lifecycle {
    replace_triggered_by = [aws_db_subnet_group.this.id]
  }

  tags = {
    Name = "${var.project_name}-db-replica"
  }
}
