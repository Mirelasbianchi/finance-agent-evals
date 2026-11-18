variable "project" {
  description = "Name prefix for every resource"
  type        = string
  default     = "finance-agent"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_repository" {
  description = "owner/repo allowed to deploy through GitHub Actions OIDC"
  type        = string
  default     = "Mirelasbianchi/finance-agent-evals"
}

variable "create_github_oidc_provider" {
  description = "Set to false if the account already has the token.actions.githubusercontent.com provider"
  type        = bool
  default     = true
}

variable "model" {
  description = "LiteLLM model the deployed agent uses. baseline/rules needs no API key."
  type        = string
  default     = "baseline/rules"
}

variable "llm_api_key_env" {
  description = "Environment variable that receives the API key secret, e.g. ANTHROPIC_API_KEY"
  type        = string
  default     = "ANTHROPIC_API_KEY"
}

variable "task_cpu" {
  type    = number
  default = 256
}

variable "task_memory" {
  type    = number
  default = 512
}
