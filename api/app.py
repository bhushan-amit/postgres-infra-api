from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import subprocess
import os

app = Flask(__name__)
api = Api(app)

class SetupPostgres(Resource):
    def post(self):
        # Get parameters from the request
        data = request.json
        instance_type = data.get('instance_type', 't2.micro')
        replica_count = data.get('replica_count', 1)
        
        env = os.environ.copy()  # Copy current environment variables
        # Set environment variables for Terraform
        env['TF_VAR_instance_type'] = instance_type
        env['TF_VAR_replica_count'] = str(replica_count)
        

        # Define the path to the Terraform directory
        terraform_dir = "/home/ubuntu/terraform"

        try:
            # Change the current working directory to the Terraform directory
            os.chdir(terraform_dir)
            print (result)
            # Initialize Terraform
            subprocess.run(["terraform", "init"], check=True)
            # Plan
            subprocess.run(["terraform", "plan"], check=True)
            # Apply
            subprocess.run(["terraform", "apply", "-auto-approve"], check=True)

            # Execute Ansible Playbook
            ansible_inventory = "/home/ubuntu/ansible/inventory/hosts"
            ansible_playbook = "/home/ubuntu/ansible/playbooks/main.yml"
           # subprocess.run(["ansible-playbook", "-i", ansible_inventory, ansible_playbook], check=True)

            return jsonify({'message': 'Infrastructure and PostgreSQL setup completed successfully.'})
        except subprocess.CalledProcessError as e:
            return jsonify({'error': str(e)}), 500

api.add_resource(SetupPostgres, '/setup')

if __name__ == '__main__':
    app.run(debug=True)

