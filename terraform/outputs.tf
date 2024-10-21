output "primary_db_public_ip" {
  value = aws_instance.primary_db.public_ip
}

output "replica_db_public_ips" {
  value = aws_instance.replica_db[*].public_ip
}

