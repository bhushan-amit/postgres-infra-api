provider "aws" {
  region = var.region
}

resource "aws_security_group" "postgres_sg" {
  name        = "postgres-sg"
  description = "Security group for PostgreSQL instances"
  
  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to all IPs (for testing). In production, lock down to specific IPs
  }
   
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["${var.allowed_cidr}"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "primary_db" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name
  security_groups = [aws_security_group.postgres_sg.name]

  tags = {
    Name = "${var.app_name}-primary-db"
  }
}

resource "aws_instance" "replica_db" {
  count         = var.replica_count
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name
  security_groups = [aws_security_group.postgres_sg.name]

  tags = {
    Name = "${var.app_name}-replica-db-${count.index + 1}"
  }
}

