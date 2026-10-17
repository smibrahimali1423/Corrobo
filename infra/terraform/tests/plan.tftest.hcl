# Offline tests: `terraform test` with a mocked AWS provider (apply is simulated),
# so they run in CI without any AWS account or credentials.

mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b"] }
  }
  mock_data "aws_ssm_parameter" {
    defaults = { value = "ami-0123456789abcdef0" }
  }
}

run "defaults_http_only_no_github_role" {
  command = apply

  assert {
    condition     = length(aws_iam_role.github_deploy) == 0
    error_message = "No GitHub deploy role should be created without github_repository."
  }

  assert {
    condition     = aws_instance.app.instance_type == "t3.medium"
    error_message = "Default instance type should be t3.medium."
  }

  assert {
    condition     = strcontains(aws_instance.app.user_data, "SITE_ADDRESS=:80")
    error_message = "Without a domain, Caddy should serve plain HTTP on :80."
  }

  assert {
    condition     = aws_instance.app.metadata_options[0].http_tokens == "required"
    error_message = "IMDSv2 must be enforced."
  }

  assert {
    condition     = alltrue([for rule in aws_security_group.web.ingress : contains([80, 443], rule.from_port)])
    error_message = "Only ports 80 and 443 may be open (no SSH)."
  }
}

run "with_domain_and_github" {
  command = apply

  variables {
    domain_name       = "corrobo.example.com"
    github_repository = "someone/Corrobo"
  }

  assert {
    condition     = strcontains(aws_instance.app.user_data, "SITE_ADDRESS=corrobo.example.com")
    error_message = "Caddy should be configured for the domain (automatic HTTPS)."
  }

  assert {
    condition     = strcontains(aws_instance.app.user_data, "CORS_ORIGINS=https://corrobo.example.com")
    error_message = "CORS origin should be the HTTPS domain."
  }

  assert {
    condition     = length(aws_iam_role.github_deploy) == 1
    error_message = "GitHub deploy role should exist when github_repository is set."
  }

  assert {
    condition     = strcontains(aws_iam_role.github_deploy[0].assume_role_policy, "repo:someone/Corrobo:ref:refs/heads/main")
    error_message = "Deploy role must be restricted to the repo's main branch."
  }
}

run "existing_oidc_provider_is_looked_up" {
  command = apply

  variables {
    github_repository           = "someone/Corrobo"
    create_github_oidc_provider = false
  }

  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 0
    error_message = "Should reuse, not create, the OIDC provider."
  }
}
