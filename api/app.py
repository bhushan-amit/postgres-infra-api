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

class ExecuteAnsible(Resource):
    def post(self):
        try:
            # Run the Ansible playbook
            ansible_inventory = "/home/ubuntu/ansible/inventory/hosts"  # Updated with the correct path
            ansible_playbook = "/home/ubuntu/ansible/playbooks/main.yml"  # Updated with the correct path

            subprocess.run(["ansible-playbook", "-i", ansible_inventory, ansible_playbook], check=True)

            return jsonify({"message": "Ansible playbook executed successfully!"})
        except subprocess.CalledProcessError as e:
            return jsonify({"error": str(e)}), 500

# Flask-Restful API resources
api.add_resource(GenerateTerraform, '/generate-terraform')
api.add_resource(PlanTerraform, '/plan-terraform')
api.add_resource(ApplyTerraform, '/apply-terraform')
api.add_resource(ExecuteAnsible, '/execute-ansible')

if __name__ == '__main__':
    app.run(debug=True)

