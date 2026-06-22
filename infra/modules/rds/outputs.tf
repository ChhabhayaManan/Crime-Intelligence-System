output "writer_endpoint" {
  description = "Primary endpoint (host:port) for all writes + migrations"
  value       = aws_db_instance.primary.endpoint
}

output "writer_address" {
  description = "Primary hostname only"
  value       = aws_db_instance.primary.address
}

output "reader_endpoint" {
  description = "Read replica endpoint (host:port); null if replica disabled"
  value       = var.create_read_replica ? aws_db_instance.replica[0].endpoint : null
}

output "reader_address" {
  description = "Read replica hostname only; null if replica disabled"
  value       = var.create_read_replica ? aws_db_instance.replica[0].address : null
}

output "port" {
  value = aws_db_instance.primary.port
}

output "db_name" {
  value = aws_db_instance.primary.db_name
}

output "db_username" {
  value = aws_db_instance.primary.username
}

output "security_group_id" {
  value = aws_security_group.rds.id
}

output "primary_arn" {
  value = aws_db_instance.primary.arn
}
