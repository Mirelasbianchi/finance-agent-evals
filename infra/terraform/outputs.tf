output "url" {
  description = "Public URL of the dashboard"
  value       = "http://${aws_lb.this.dns_name}"
}

output "ecr_repository" {
  value = aws_ecr_repository.api.repository_url
}

output "llm_api_key_secret" {
  description = "Put your model API key here if you switch var.model to an LLM"
  value       = aws_secretsmanager_secret.llm_api_key.name
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_ROLE_ARN repository variable in GitHub"
  value       = aws_iam_role.github_deploy.arn
}
