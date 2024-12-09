module "vpc" {
  source         = "./modules/vpc"
  cidr_block     = "10.0.0.0/16"
  public_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = ["10.0.3.0/24", "10.0.4.0/24"]
}

# ECS Cluster
module "ecs" {
  source          = "./modules/ecs"
  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnets
  public_subnets  = module.vpc.public_subnets
}

# RDS (MongoDB or equivalent setup)
module "rds" {
  source        = "./modules/rds"
  db_name       = "logs"
  instance_type = "db.t3.micro"
  engine        = "postgres"
  username      = "admin"
  password      = data.aws_secretsmanager_secret_version.db_password.secret_string
  vpc_id        = module.vpc.vpc_id
  subnets       = module.vpc.private_subnets
}

# Redis (ElastiCache)
module "redis" {
  source      = "./modules/redis"
  engine      = "redis"
  node_type   = "cache.t2.micro"
  vpc_id      = module.vpc.vpc_id
  subnets     = module.vpc.private_subnets
}

# ALB
module "alb" {
  source         = "./modules/alb"
  vpc_id         = module.vpc.vpc_id
  public_subnets = module.vpc.public_subnets
  target_groups  = [{
    name     = "api-target-group"
    protocol = "HTTP"
    port     = 80
  }]
}

# ECS Service
resource "aws_ecs_service" "log_processing_api" {
  cluster        = module.ecs.cluster_id
  name           = "log-processing-api"
  launch_type    = "FARGATE"
  desired_count  = 2
  task_definition = aws_ecs_task_definition.log_processing_api.arn

  network_configuration {
    subnets         = module.vpc.private_subnets
    security_groups = [module.vpc.default_security_group]
  }

  load_balancer {
    target_group_arn = module.alb.target_group_arns[0]
    container_name   = "log-processing-container"
    container_port   = 80
  }
}

# CloudWatch for ECS Logs
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/log-processing-api"
  retention_in_days = 30
}
