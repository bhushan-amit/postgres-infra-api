#!/bin/bash

# Fetch the public IP addresses from Terraform outputs
primary_ip=$(terraform output -raw primary_db_public_ip)
replica_ips=$(terraform output -json replica_db_public_ips | jq -r '.[]')

# Path to store the generated Ansible inventory
inventory_path="/home/ubuntu/terraform/hosts"

# Ensure the directory exists
mkdir -p ansible/inventory

# Generate Ansible inventory file
echo "[primary]" > $inventory_path
echo "primary-db ansible_host=$primary_ip ansible_user=ubuntu ansible_ssh_private_key_file=/home/ubuntu/imamit.a001.pem" >> $inventory_path
echo "" >> $inventory_path

echo "[replicas]" >> $inventory_path
for ip in $replica_ips; do
  echo "replica-db ansible_host=$ip ansible_user=ubuntu ansible_ssh_private_key_file=/home/ubuntu/imamit.a001.pem" >> $inventory_path
done

echo "" >> $inventory_path
echo "Ansible inventory file generated at $inventory_path"

