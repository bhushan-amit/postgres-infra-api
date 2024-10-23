from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import os
import subprocess
from jinja2 import Template

app = Flask(__name__)
api = Api(app)

# Function to dynamically generate the main.tf content
def generate_main_tf(instance_type, replica_count):
    template = """
    provider "aws" {
      region = "ap-south-1"
    }

    resource "aws_security_group" "postgres_sg" {
      name        = "postgres-sg"
      description = "Security group for PostgreSQL instances"

      ingress {
        description = "Allow SSH"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]  # Allowing SSH from all IPs. This should be locked down in production.
      }

      ingress {
        from_port   = 5432
        to_port     = 5432
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]  # Allowing PostgreSQL traffic from all IPs. Modify this in production.
      }

      egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }
    }

    resource "aws_instance" "primary_db" {
      ami           = "ami-0dee22c13ea7a9a67"
      instance_type = "{{ instance_type }}"
      security_groups = [aws_security_group.postgres_sg.name]

      tags = {
        Name = "chalo-primary-db"
      }
    }

    resource "aws_instance" "replica_db" {
      count         = {{ replica_count }}
      ami           = "ami-0dee22c13ea7a9a67"
      instance_type = "{{ instance_type }}"
      security_groups = [aws_security_group.postgres_sg.name]

      tags = {
        Name = "chalo-replica-db-${count.index + 1}"
      }
    }
    """
    # Create the Jinja2 template object
    tf_template = Template(template)
    # Render the template with the provided instance_type and replica_count
    rendered_template = tf_template.render(instance_type=instance_type, replica_count=replica_count)
    return rendered_template

# Function to dynamically generate the outputs.tf content
def generate_outputs_tf():
    outputs_template = """
    output "primary_db_public_ip" {
      value = aws_instance.primary_db.public_ip
    }

    output "replica_db_public_ips" {
      value = aws_instance.replica_db[*].public_ip
    }
    """
    return outputs_template

# Function to write the generated Terraform files to disk
def write_terraform_files(main_tf_content, outputs_tf_content):
    terraform_dir = "/home/ubuntu/TF"  # Updated to use /home/ubuntu/TF
    os.makedirs(terraform_dir, exist_ok=True)

    # Write the main.tf file
    with open(os.path.join(terraform_dir, "main.tf"), "w") as f:
        f.write(main_tf_content)

    # Write the outputs.tf file
    with open(os.path.join(terraform_dir, "outputs.tf"), "w") as f:
        f.write(outputs_tf_content)

class GenerateTerraform(Resource):
    def post(self):
        # Get parameters from the request
        data = request.json
        instance_type = data.get('instance_type', 't2.micro')  # Default to t2.micro
        replica_count = data.get('replica_count', 1)  # Default to 1 replica

        # Generate the main.tf and outputs.tf content
        main_tf_content = generate_main_tf(instance_type, replica_count)
        outputs_tf_content = generate_outputs_tf()

        # Write the content to the Terraform files
        write_terraform_files(main_tf_content, outputs_tf_content)

        return jsonify({"message": "Terraform configuration generated successfully!"})

class PlanTerraform(Resource):
    def post(self):
        try:
            terraform_dir = "/home/ubuntu/TF"  # Updated to use /home/ubuntu/TF
            os.chdir(terraform_dir)

            # Initialize Terraform
            subprocess.run(["terraform", "init"], check=True)

            # Run Terraform Plan and capture the output
            result = subprocess.run(["terraform", "plan", "-no-color"], capture_output=True, text=True, check=True)
            return jsonify({"message": "Terraform plan executed successfully!", "output": result.stdout})
        except subprocess.CalledProcessError as e:
            return jsonify({"error": str(e), "output": e.stdout}), 500

class ApplyTerraform(Resource):
    def post(self):
        try:
            terraform_dir = "/home/ubuntu/TF"  # Updated to use /home/ubuntu/TF
            os.chdir(terraform_dir)

            # Apply the Terraform plan and capture the output
            result = subprocess.run(["terraform", "apply", "-auto-approve"], capture_output=True, text=True, check=True)

            # Return the successful message along with output
            return jsonify({"message": "Terraform applied successfully!", "output": result.stdout})
        except subprocess.CalledProcessError as e:
            # Capture the output on error
            return jsonify({"error": str(e), "output": e.stderr}), 500


class CreateAnsibleScript(Resource):
    def post(self):
        try:
            self.create_inventory()

            # self.create_main_playbook()

            return jsonify({"message": "Ansible inventory and playbook created successfully!"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def create_inventory(self):
        terraform_dir = "/home/ubuntu/TF"
        os.chdir(terraform_dir)

        # Define the shell script to generate Ansible inventory
        inventory_script = """
#!/bin/bash

# Fetch the public IP addresses from Terraform outputs
primary_ip=$(terraform output -raw primary_db_public_ip)
replica_ips=$(terraform output -json replica_db_public_ips | jq -r '.[]')

# Path to store the generated Ansible inventory
inventory_path="/home/ubuntu/ansible/inventory/hosts"
mkdir -p "$(dirname "$inventory_path")"

# Generate Ansible inventory file
echo "[primary]" > $inventory_path
echo "primary-db ansible_host=$primary_ip ansible_user=ubuntu ansible_ssh_private_key_file=/home/ubuntu/imamit.a001.pem" >> $inventory_path
echo "" >> $inventory_path

echo "[replicas]" >> $inventory_path
for ip in $replica_ips; do
  echo "replica-db ansible_host=$ip ansible_user=ubuntu ansible_ssh_private_key_file=/home/ubuntu/imamit.a001.pem" >> $inventory_path
done

echo "" >> $inventory_path
"""

        # Write the inventory script to a temporary file
        script_path = "/home/ubuntu/TF/generate_inventory.sh"
        with open(script_path, 'w') as f:
            f.write(inventory_script.strip())

        # Make the script executable
        subprocess.run(["chmod", "+x", script_path], check=True)

        # Execute the inventory script
        subprocess.run([script_path], check=True)

    def create_main_playbook(self):
        # Path to the main playbook
        playbook_path = "/home/ubuntu/ansible/main.yml"

        # Define the content of the main playbook
        playbook_content = """
---
- name: Setup PostgreSQL on All Servers
  hosts: all  # Targets both primary and replica hosts
  become: yes
  tasks:
    - name: Install PostgreSQL
      include_tasks: tasks/install.yml

- name: Apply PostgreSQL configuration
  hosts: all
  become: yes
  tasks:
    - include_tasks: tasks/configure_postgres.yml

- name: Configure PostgreSQL Primary
  hosts: primary-db
  become: yes
  tasks:
    - include_tasks: tasks/configure_primary.yml

- name: Configure PostgreSQL Replicas
  hosts: replica-db
  become: yes
  tasks:
    - include_tasks: tasks/configure_replica.yml
        """

        # Write the playbook content to the file
        with open(playbook_path, 'w') as f:
            f.write(playbook_content.strip())

class ExecuteAnsibleScript(Resource):
    def post(self):
        try:
            # Execute the Ansible playbook
            playbook_path = "/home/ubuntu/ansible/main.yml"
            subprocess.run(["ansible-playbook", playbook_path], check=True)

            return jsonify({"message": "Ansible playbook executed successfully!"})
        except subprocess.CalledProcessError as e:
            return jsonify({"error": str(e), "output": e.stdout}), 500


# Flask-Restful API resources
api.add_resource(GenerateTerraform, '/generate-terraform')
api.add_resource(PlanTerraform, '/plan-terraform')
api.add_resource(ApplyTerraform, '/apply-terraform')
api.add_resource(CreateAnsibleScript, '/create-ansible-script')
api.add_resource(ExecuteAnsibleScript, '/execute-ansible-script')

if __name__ == '__main__':
    app.run(debug=True)

