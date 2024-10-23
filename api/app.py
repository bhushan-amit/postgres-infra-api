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
      key_name      = "imamit.a001"
      security_groups = [aws_security_group.postgres_sg.name]

      tags = {
        Name = "chalo-primary-db"
      }
    }

    resource "aws_instance" "replica_db" {
      count         = {{ replica_count }}
      ami           = "ami-0dee22c13ea7a9a67"
      instance_type = "{{ instance_type }}"
      key_name      = "imamit.a001"
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

            data = request.json
            max_connections = data.get ('max_connections', '100')
            shared_buffers = data.get ('shared_buffers', '256MB')
            self.create_main_playbook(max_connections, shared_buffers)

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

counter = 1
echo "[replica]" >> $inventory_path
for ip in $replica_ips; do
  echo "replica-db${counter} ansible_host=$ip ansible_user=ubuntu ansible_ssh_private_key_file=/home/ubuntu/imamit.a001.pem" >> $inventory_path
  ((counter++))
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

    def create_main_playbook(self, max_connections, shared_buffers):
        # Path to the main playbook
        playbook_path = "/home/ubuntu/ansible/main.yml"
        print ("Hello")
        # Define the template for the main playbook
        playbook_template = """
---
- name: Setup PostgreSQL on All Servers
  hosts: all  # Targets both primary and replica hosts
  become: yes
  tasks:
    - name: Install PostgreSQL
      apt:
        update_cache: yes
        name:
          - postgresql
          - postgresql-contrib
        state: present

    - name: Ensure PostgreSQL is running and enabled
      systemd:
        name: postgresql
        state: started
        enabled: yes

    - name: Install ACL
      apt:
        name: acl
        state: present
      when: "'primary' in group_names"

    - name: Install psycopg2
      apt:
        name: python3-psycopg2
        state: present
      when: "'primary' in group_names"

    - name: Update PostgreSQL configuration and restart service
      lineinfile:
        path: /etc/postgresql/16/main/postgresql.conf
        regexp: '^max_connections'
        line: 'max_connections = {{ max_connections }}'

    - name: Update shared_buffers to '{{ shared_buffers }}'
      lineinfile:
        path: /etc/postgresql/16/main/postgresql.conf
        regexp: '^shared_buffers'
        line: "shared_buffers = '{{ shared_buffers }}'"
{% raw %}
    - name: Configure PostgreSQL for replication (Primary)
      lineinfile:
        path: /etc/postgresql/16/main/postgresql.conf
        regexp: "{{ item.regexp }}"
        line: "{{ item.line }}"
      loop:
        - { regexp: '^#wal_level', line: 'wal_level = logical' }
        - { regexp: '^#wal_log_hints', line: 'wal_log_hints = on' }
        - { regexp: '^#max_wal_senders', line: 'max_wal_senders = 5' }
        - { regexp: '^#listen_addresses', line: "listen_addresses = '*'" }
      when: "'primary' in group_names" 

    - name: Allow replication connections from replicas (Primary)
      lineinfile:
        path: /etc/postgresql/16/main/pg_hba.conf
        line: "host replication all {{ item }}/32 md5"
      loop: "{{ groups['replica'] | map('extract', hostvars, 'ansible_host') | list }}"
      when: "'primary' in group_names" 

    - name: Create replication user
      postgresql_user:
        state: present
        name: replica_user
        password: replica_password
        role_attr_flags: REPLICATION
      become: true
      become_user: postgres
      when: "'primary' in group_names" 

    - name: Restart PostgreSQL to apply changes
      systemd:
        name: postgresql
        state: restarted
      when: "'primary' in group_names" 

    - name: Stop PostgreSQL service on replica
      systemd:
        name: postgresql
        state: stopped
      when: "'replica' in group_names"

    - name: Clear existing PostgreSQL data directory
      file:
        path: /var/lib/postgresql/16/main
        state: absent
      become: true
      when: "'replica' in group_names"

    - name: Set replication slot name
      set_fact:
        replication_slot_name: "replica_{{ inventory_hostname | regex_replace('-', '_') }}"
      when: "'replica' in group_names"

    - name: Copy data from primary node
      command: >
        pg_basebackup -h {{ hostvars['primary-db'].ansible_host }} -U replica_user -X stream -C -S {{ replication_slot_name }} -v -R -D /var/lib/postgresql/16/main/
      become: true
      environment:
        PGPASSWORD: 'replica_password'
      when: "'replica' in group_names"

{% endraw %}
    - name: Ensure correct ownership of the PostgreSQL data directory
      file:
        path: /var/lib/postgresql/16/main
        state: directory
        owner: postgres
        group: postgres
        recurse: yes
      become: true
      when: "'replica' in group_names"

    - name: Start PostgreSQL service on replica
      systemd:
        name: postgresql
        state: started
      when: "'replica' in group_names"

"""        

        # Render the playbook content using Jinja2
        template = Template(playbook_template)
        rendered_playbook_content = template.render(max_connections=max_connections, shared_buffers=shared_buffers)

        # Write the rendered playbook content to the file
        with open(playbook_path, 'w') as f:
            f.write(rendered_playbook_content)


class ExecuteAnsibleScript(Resource):
    def post(self):
        try:
            # Execute the Ansible playbook
            ansible_inventory = "/home/ubuntu/ansible/inventory/hosts"
            playbook_path = "/home/ubuntu/ansible/main.yml"
            subprocess.run(["ansible-playbook", "-i", ansible_inventory, playbook_path], check=True)

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

