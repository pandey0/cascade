# Cascade gateway on AWS ECS Fargate. NOT APPLIED: written and reviewed only (see ../README.md).
# Cost-aware defaults: one 0.25 vCPU / 512 MB task, no NAT gateway (public subnets), short log retention.
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.region
  default_tags { tags = { project = "cascade", managed_by = "terraform" } }
}

data "aws_vpc" "default" { default = true }
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_ecr_repository" "gateway" {
  name                 = "cascade-gateway"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true # teardown friendliness
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/cascade/gateway"
  retention_in_days = var.log_retention_days
}

# Secrets are created empty; set values out of band (never in Terraform state or git).
resource "aws_secretsmanager_secret" "api_keys" { name = "cascade/api-keys" }
resource "aws_secretsmanager_secret" "teacher_key" { name = "cascade/teacher-api-key" }

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "cascade-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}
resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
data "aws_iam_policy_document" "read_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.api_keys.arn, aws_secretsmanager_secret.teacher_key.arn]
  }
}
resource "aws_iam_role_policy" "read_secrets" {
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.read_secrets.json
}

resource "aws_security_group" "alb" {
  name   = "cascade-alb"
  vpc_id = data.aws_vpc.default.id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "task" {
  name   = "cascade-task"
  vpc_id = data.aws_vpc.default.id
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "gateway" {
  name               = "cascade"
  load_balancer_type = "application"
  subnets            = data.aws_subnets.default.ids
  security_groups    = [aws_security_group.alb.id]
}
resource "aws_lb_target_group" "gateway" {
  name        = "cascade"
  port        = 8080
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = data.aws_vpc.default.id
  health_check {
    path    = "/healthz"
    matcher = "200"
  }
}
locals {
  tls = var.certificate_arn != ""
}

# Plain HTTP only when no certificate is given (demo). With a certificate, port 80 redirects to 443.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.gateway.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = local.tls ? "redirect" : "forward"
    target_group_arn = local.tls ? null : aws_lb_target_group.gateway.arn
    dynamic "redirect" {
      for_each = local.tls ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = local.tls ? 1 : 0
  load_balancer_arn = aws_lb.gateway.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gateway.arn
  }
}

resource "aws_ecs_cluster" "this" { name = "cascade" }

resource "aws_ecs_task_definition" "gateway" {
  family                   = "cascade-gateway"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  container_definitions = jsonencode([{
    name                   = "gateway"
    image                  = "${aws_ecr_repository.gateway.repository_url}:${var.image_tag}"
    essential              = true
    readonlyRootFilesystem = true
    portMappings           = [{ containerPort = 8080 }]
    environment = [
      { name = "CASCADE_RATE_LIMIT_PER_MIN", value = tostring(var.rate_limit_per_min) },
    ]
    secrets = [
      { name = "CASCADE_API_KEYS", valueFrom = aws_secretsmanager_secret.api_keys.arn },
      { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.teacher_key.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.gateway.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "gateway"
      }
    }
  }])
}

resource "aws_ecs_service" "gateway" {
  name            = "gateway"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.gateway.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = true # avoids a NAT gateway (cost); tasks accept traffic only from the ALB SG
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.gateway.arn
    container_name   = "gateway"
    container_port   = 8080
  }
  depends_on = [aws_lb_listener.http, aws_lb_listener.https]
}
