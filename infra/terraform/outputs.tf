output "alb_dns_name" { value = aws_lb.gateway.dns_name }
output "ecr_repository_url" { value = aws_ecr_repository.gateway.repository_url }
