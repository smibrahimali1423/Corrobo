output "public_ip" {
  description = "Elastic IP of the app server. Point your domain's A record here."
  value       = aws_eip.app.public_ip
}

output "app_url" {
  value = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_eip.app.public_ip}"
}

output "instance_id" {
  description = "Use with `aws ssm start-session --target <id>` and as the EC2_INSTANCE_ID GitHub variable."
  value       = aws_instance.app.id
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN GitHub variable."
  value       = local.enable_github ? aws_iam_role.github_deploy[0].arn : null
}
