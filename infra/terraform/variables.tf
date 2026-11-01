variable "region" {
  type    = string
  default = "ap-south-1"
}
variable "image_tag" {
  type    = string
  default = "0.1.0"
}
variable "cpu" {
  type    = number
  default = 256
}
variable "memory" {
  type    = number
  default = 512
}
variable "desired_count" {
  type    = number
  default = 1
}
variable "log_retention_days" {
  type    = number
  default = 7
}
variable "rate_limit_per_min" {
  type    = number
  default = 600
}
variable "allowed_cidrs" {
  type        = list(string)
  description = "Who may reach the ALB. No default on purpose: choose your own IP, not 0.0.0.0/0."
}
variable "certificate_arn" {
  type        = string
  default     = ""
  description = "ACM certificate ARN. Empty = plain HTTP (demo only). Set it before any real traffic."
}
