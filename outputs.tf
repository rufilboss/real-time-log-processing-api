output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.dns_name
}

output "rds_endpoint" {
  description = "RDS Endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis Endpoint"
  value       = module.redis.endpoint
}
