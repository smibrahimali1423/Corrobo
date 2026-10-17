data "aws_caller_identity" "current" {}

# Latest Amazon Linux 2023 AMI, resolved via AWS's public SSM parameter.
data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

locals {
  ssm_prefix     = trimsuffix(var.ssm_parameter_prefix, "/")
  ssm_param_arns = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.ssm_prefix}/*"
}

# ---- Instance role: what the EC2 box itself may do ---------------------------

resource "aws_iam_role" "instance" {
  name = "${var.project}-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Session Manager shell access + Run Command (used by the deploy workflow).
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "read_app_secrets" {
  name = "read-app-secrets"
  role = aws_iam_role.instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = local.ssm_param_arns
      },
      {
        # SecureString decryption with the AWS-managed aws/ssm key, only via SSM.
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = "*"
        Condition = {
          StringEquals = { "kms:ViaService" = "ssm.${var.aws_region}.amazonaws.com" }
        }
      },
    ]
  })
}

resource "aws_iam_instance_profile" "instance" {
  name = "${var.project}-instance"
  role = aws_iam_role.instance.name
}

# ---- Storage -----------------------------------------------------------------

# Data lives on its own volume so replacing the instance (new AMI, resize)
# keeps the database. prevent_destroy guards against `terraform destroy`
# deleting it by accident -- remove that line deliberately if you mean it.
resource "aws_ebs_volume" "data" {
  availability_zone = aws_subnet.public.availability_zone
  size              = var.data_volume_gb
  type              = "gp3"
  encrypted         = true

  tags = { Name = "${var.project}-data" }

  lifecycle {
    prevent_destroy = true
  }
}

# ---- Instance ----------------------------------------------------------------

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023_ami.value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.instance.name

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }

  user_data_replace_on_change = true
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    aws_region             = var.aws_region
    data_volume_id         = aws_ebs_volume.data.id
    ecr_repository_url     = aws_ecr_repository.api.repository_url
    ssm_prefix             = local.ssm_prefix
    site_address           = var.domain_name != "" ? var.domain_name : ":80"
    cors_origins           = var.domain_name != "" ? "https://${var.domain_name}" : ""
    docker_compose_version = var.docker_compose_version
    compose_file_b64       = filebase64("${path.module}/../../deploy/docker-compose.prod.yml")
    caddyfile_b64          = filebase64("${path.module}/../../deploy/Caddyfile")
    deploy_script_b64      = filebase64("${path.module}/../../deploy/deploy.sh")
  })

  tags = { Name = "${var.project}-app" }

  lifecycle {
    # A new AL2023 release shouldn't silently replace the instance on the next
    # apply; bump the AMI deliberately (terraform apply -replace=...).
    ignore_changes = [ami]
  }
}

resource "aws_volume_attachment" "data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.app.id
}

resource "aws_eip" "app" {
  domain   = "vpc"
  instance = aws_instance.app.id

  tags = { Name = "${var.project}-eip" }
}
