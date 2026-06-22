locals {
  name = lower(var.project_name)
}

resource "aws_s3_bucket" "evidence" {
  bucket = var.bucket_name

  tags = {
    Name    = var.bucket_name
    Project = var.project_name
  }
}

# Block every form of public access.
resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket                  = aws_s3_bucket.evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Keep prior object versions (evidence integrity / accidental-overwrite recovery).
resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Default SSE-S3 (AES256, free) so objects are encrypted even if a client
# omits the encryption header.
resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Bucket policy: force TLS, and allow object access only to the ECS task role.
# Public access is already killed by the access block above; this is the
# "only the task role" half (defense in depth alongside the role's own policy).
data "aws_iam_policy_document" "evidence" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["s3:*"]
    resources = [aws_s3_bucket.evidence.arn, "${aws_s3_bucket.evidence.arn}/*"]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid    = "AllowTaskRoleObjectAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [var.task_role_arn]
    }

    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.evidence.arn}/*"]
  }

  # Bucket-level: HeadBucket / list for the readiness check.
  statement {
    sid    = "AllowTaskRoleBucketList"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [var.task_role_arn]
    }

    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.evidence.arn]
  }
}

resource "aws_s3_bucket_policy" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  policy = data.aws_iam_policy_document.evidence.json

  # Don't let the policy apply race ahead of the public-access block.
  depends_on = [aws_s3_bucket_public_access_block.evidence]
}
