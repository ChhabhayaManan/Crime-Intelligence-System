# terraform backend configuration for storing the state file in an S3 bucket with encryption and locking enabled
terraform {
  backend "s3" {
    bucket       = "crime-is-terraform-state"
    key          = "main/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}
