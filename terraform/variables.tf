variable "region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-south-1"
}

variable "ami_id" {
  description = "AMI ID for the instances"
  type        = string
  default     = "ami-0dee22c13ea7a9a67"
}

variable "instance_type" {
  description = "Instance type for the instances"
  type        = string
  default     = "t2.micro"
}

variable "key_name" {
  description = "Key pair name for SSH access"
  type        = string
}

variable "replica_count" {
  description = "Number of read replicas"
  type        = number
  default     = 1
}

variable "allowed_cidr" {
  description = "CIDR block for allowed ingress traffic"
  type        = string
  default     = "0.0.0.0/0"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "chalo"
}

