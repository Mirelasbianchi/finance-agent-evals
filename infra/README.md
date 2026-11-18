# Infrastructure (AWS)

The Streamlit app runs as a container on **ECS Fargate behind an Application Load Balancer**
(the ALB carries Streamlit's WebSocket connection). Terraform in [`terraform/`](terraform)
creates:

| Piece | Resource |
|---|---|
| Registry | ECR repository with scan on push, keeps the last 10 images |
| Compute | ECS Fargate service, 0.25 vCPU / 0.5 GB, circuit breaker with rollback |
| Traffic | ALB on port 80, health check on `/_stcore/health` |
| Secrets | `finance-agent/llm-api-key` in Secrets Manager, injected as `ANTHROPIC_API_KEY` |
| Logs | CloudWatch log group `/ecs/finance-agent`, 14-day retention |
| CI/CD | GitHub OIDC deploy role limited to this repository's `main` branch |

By default the deployed agent is `baseline/rules`, so it costs nothing per question and
needs no key. To serve an LLM, set the key and the model:

```bash
aws secretsmanager put-secret-value --secret-id finance-agent/llm-api-key --secret-string "$ANTHROPIC_API_KEY"
terraform apply -var model=anthropic/claude-sonnet-4-5
```

## First deploy

```bash
cd infra/terraform
terraform init
terraform apply
terraform output
```

In GitHub, **Settings → Secrets and variables → Actions → Variables**: set `AWS_ROLE_ARN`
(`terraform output -raw github_deploy_role_arn`) and `AWS_REGION`, then run the
**Deploy to AWS** workflow once. After that every green CI run on `main` deploys.

Rough cost in `us-east-1`: about **US$ 25–30 per month** (load balancer plus one small
Fargate task). `terraform destroy` removes everything.
