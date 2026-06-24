output "vpc_id" {
  value = aws_vpc.main.id
}

output "igw_id" {
  value = aws_internet_gateway.igw.id
}

output "public_subnet_ids" {
  value = [aws_subnet.public_az1.id, aws_subnet.public_az2.id]
}

output "private_subnet_ids" {
  value = [aws_subnet.private_az1.id, aws_subnet.private_az2.id]
}

# Tiered subnet contract consumed by other modules. app == the existing private
# (backend) subnets; frontend and data are the new tiers.
output "app_subnet_ids" {
  value = [aws_subnet.private_az1.id, aws_subnet.private_az2.id]
}

output "frontend_subnet_ids" {
  value = [aws_subnet.frontend_az1.id, aws_subnet.frontend_az2.id]
}

output "data_subnet_ids" {
  value = [aws_subnet.data_az1.id, aws_subnet.data_az2.id]
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "availability_zones" {
  value = slice(data.aws_availability_zones.available.names, 0, 2)
}

output "public_route_table_id" {
  value = aws_route_table.public.id
}

# List form so it feeds the S3 gateway endpoint's route_table_ids directly.
output "private_route_table_ids" {
  value = [aws_route_table.private.id]
}
