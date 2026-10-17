variable "project" {
  description = "Name prefix for all resources."
  type        = string
  default     = "corrobo"
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type. The embedding model + Postgres need ~2-3 GB RAM; t3.medium (4 GB) is the smallest comfortable size."
  type        = string
  default     = "t3.medium"
}

variable "root_volume_gb" {
  description = "Root EBS volume size (OS + Docker images; the API image with torch is several GB)."
  type        = number
  default     = 30
}

variable "data_volume_gb" {
  description = "Separate EBS volume for Postgres, Chroma and Caddy data. Survives instance replacement."
  type        = number
  default     = 20
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "domain_name" {
  description = "Optional domain (e.g. corrobo.example.com) pointed at the Elastic IP. When set, Caddy serves HTTPS with an automatic Let's Encrypt certificate. Empty = plain HTTP on port 80."
  type        = string
  default     = ""
}

variable "ssm_parameter_prefix" {
  description = "SSM Parameter Store path holding the app's secrets (created manually, see docs/DEPLOYMENT.md)."
  type        = string
  default     = "/corrobo"
}

variable "github_repository" {
  description = "GitHub repo (owner/name) allowed to deploy via OIDC, e.g. \"smibrahimali1423/Corrobo\". Empty = don't create the deploy role."
  type        = string
  default     = ""
}

variable "create_github_oidc_provider" {
  description = "Create the account-wide GitHub OIDC provider. Set false if your AWS account already has one for token.actions.githubusercontent.com."
  type        = bool
  default     = true
}

variable "docker_compose_version" {
  description = "Docker Compose v2 plugin release installed on the instance."
  type        = string
  default     = "v2.32.4"
}
