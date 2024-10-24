# Postgres Infrastructure API

This repository contains  Ansible playbooks, Terraform configurations and a Flask API to manage and deploy a PostgreSQL database infrastructure on AWS. The infrastructure includes a primary database instance and multiple replicas using Terraform and AWS. Ansible is used for further configuration of the database setup.

## Features

- Deploy a PostgreSQL infrastructure with a primary instance and multiple replicas with replication configured
- Manage infrastructure through a Flask API.
- Dynamically generate an Ansible inventory based on Terraform output.
- Automate infrastructure provisioning and database configuration.

## References

- https://www.cherryservers.com/blog/how-to-set-up-postgresql-database-replication
  
## Table of Contents

1. [Requirements](#requirements)
2. [Flask Setup](#installation)
3. [Available API Endpoints](#available-api-endpoints)
4. [Usage](#usage)
5. [Repository Structure](#repository-structure-after-running-all-the-scripts)
6. [Troubleshooting] (#troubleshooting)
7. [Testing the Replication Setup](#testing-the-replication-setup)


---

## Requirements

Before getting started, ensure that you have the following tools installed on your local or remote server:

- Python 3.x
- [Terraform](https://www.terraform.io/downloads)
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
- AWS credentials configured in your environment (for example using `aws configure`)

## Installation

### Creating a Virtual Environment and Running the Application

To ensure that your Python dependencies are isolated and do not interfere with other projects, it's a good practice to use a virtual environment. Here are the steps to create a virtual environment and run the Flask application:

### 1. Create a Virtual Environment

Navigate to the root of your project directory and run the following command to create a virtual environment:

```bash
python -m venv venv
```

This command will create a new directory named `venv` in your project folder, which will contain the Python interpreter and libraries for your project.

### 2. Activate the Virtual Environment

Activate the virtual environment using the following command:

- **On Windows**:

  ```bash
  venv\Scripts\activate
  ```

- **On macOS and Linux**:

  ```bash
  source venv/bin/activate
  ```

After activation, your command prompt will change to indicate that the virtual environment is active.

### 3. Install the Required Dependencies

With the virtual environment activated, install the required dependencies from the `requirements.txt` file:

```bash
pip install -r api/requirements.txt
```

### 4. Run the Flask Application

Now you can run the Flask application. Make sure you are still in the `api` directory and execute the following command:

```bash
python app.py
```

The Flask application will start running on `http://127.0.0.1:5000` by default.

### 3. Install Terraform and Ansible

Ensure Terraform and Ansible are properly installed and available on your system.

- Terraform installation: [Terraform Install Guide](https://developer.hashicorp.com/terraform/downloads)
- Ansible installation: [Ansible Install Guide](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

  Install AWS Cli and configure your AWS credentials for interacting with AWS and Terraform

## Assumptions

### 1. We have a pem key handy in our AWS account and local machine, which we will use as pem key for connecting with ansible hosts

One can easily send their local keys to the machine using scp or pscp command.

## Available API Endpoints

### /generate-terraform (POST)

This endpoint generates the Terraform configuration for the specified instance type and replica count.

### /plan-terraform (POST)

This endpoint creates a Terraform plan for the infrastructure deployment.

### /apply-terraform (POST)

This endpoint applies the Terraform configuration to provision the infrastructure.

### /create-ansible-script (POST)

This endpoint creates an Ansible script for configuring the PostgreSQL instances.

### /execute-ansible-script (POST)

This endpoint executes the generated Ansible script on the infrastructure provisioned by Terraform.

## Usage

To set up your PostgreSQL read-replicas infrastructure, follow the steps below:

1. **Generate Terraform Configuration**:
   Use the following command to generate the Terraform configuration for your infrastructure:

   ```bash
   curl -X POST http://localhost:5000/generate-terraform \
   -H "Content-Type: application/json" \
   -d '{"instance_type": "t2.medium", "replica_count": 2}'
   ```

2. **Plan Terraform Deployment**:
   After generating the configuration, plan the deployment with:

   ```bash
   curl -X POST http://localhost:5000/plan-terraform \
   -H "Content-Type: application/json"
   ```

3. **Apply Terraform Deployment**:
   Once the plan is ready, apply the Terraform configuration to create the infrastructure:

   ```bash
   curl -X POST http://localhost:5000/apply-terraform \
   -H "Content-Type: application/json"
   ```

4. **Create Ansible Script**:
   Next, create the Ansible script for configuring the PostgreSQL instances:

   ```bash
   curl -X POST http://localhost:5000/create-ansible-script \
   -H "Content-Type: application/json" \
   -d '{"max_connections": 200, "shared_buffers": "128MB"}'
   ```

5. **Execute Ansible Script**:
   Finally, execute the Ansible script to configure the PostgreSQL instances:

   ```bash
   curl -X POST http://localhost:5000/execute-ansible-script \
   -H "Content-Type: application/json"
   ```

## Repository Structure After Running all the Scripts

```bash
postgres-infra-api/
├── api/                    # Flask API application
│   ├── app.py              # Flask application
│   ├── requirements.txt    # Python requirements
├── ansible/        # Ansible playbooks for PostgreSQL setup
│   ├── main.yml/
│   ├── inventory/
|       ├──hosts         # Generated dynamically
├── terraform/               # Terraform scripts for AWS infrastructure
│   ├── main.tf
│   ├── outputs.tf
├── imamit.a001.pem
```


## Troubleshooting


### 1. Ensuring SSH Access to EC2 Instances
When creating EC2 instances using Terraform, ensure that the correct SSH key file is configured and accessible. Verify that the key file used during instance creation is the same as the one specified for SSH access.

Alternatively, if SSH access is not feasible, you can configure Ansible to connect via AWS Systems Manager (SSM). Refer to the official Ansible and AWS documentation for detailed instructions on setting up Ansible with SSM.

### 2. Resolving "Max WAL Senders Limit Exceeded"
The `max_wal_senders` parameter in PostgreSQL controls the maximum number of concurrent WAL (Write-Ahead Logging) sender processes, which are required for streaming replication and base backups. If you encounter a "Max WAL Senders Limit Exceeded" error, increase the `max_wal_senders` value in the PostgreSQL configuration file (`postgresql.conf`) to accommodate more concurrent senders.

### 3. Addressing First-Time SSH Connections in Ansible
When running Ansible for the first time, you may need to confirm the authenticity of each host by typing "yes" to proceed with the SSH connection. If you are prompted multiple times, you need to respond "yes" for each host. Sometimes, partial connections may cause the script to proceed without completing the full process, requiring you to rerun the playbook.

### 4. Fixing "Replication Slot Already Exists" Error
If you encounter an error indicating that a replication slot already exists but replication is not functioning as expected, you can drop the existing replication slot on the primary database and rerun the playbook. This happens due to a partial run of Ansible script.  Use the following SQL command to drop the replication slot:

```sql
SELECT pg_drop_replication_slot('replica_replica_db1');
```

Once the slot is dropped, rerun the playbook to successfully recreate the slot and complete the replication setup.


## Testing the Replication Setup

After setting up replication, it is important to verify that the replica node is correctly connected to the primary node and that the replication is working as intended.

### Step 1: Verify the Replication State

1. **On the Primary Server**:

   - Log into the primary server and switch to the `postgres` user:

     ```bash
     sudo -u postgres psql
     ```

   - Query the `pg_stat_replication` table to check if the replica is connected and replication is active:

     ```sql
     SELECT client_addr, state FROM pg_stat_replication;
     SELECT * FROM pg_stat_replication;
     ```

   - You should see information regarding the replica’s IP address and the replication state, confirming that the replication setup is active.

### Step 2: Test Data Replication

1. **Create a Test Database and Table on the Primary Server**:

   - Create a new database to test replication:

     ```sql
     CREATE DATABASE students_db;
     ```

   - Connect to the new database:

     ```sql
     \c students_db;
     ```

   - Create a table inside the `students_db` database:

     ```sql
     CREATE TABLE student_details (first_name VARCHAR(15), last_name VARCHAR(15), email VARCHAR(40));
     ```

   - Insert a test record into the `student_details` table:

     ```sql
     INSERT INTO student_details (first_name, last_name, email)
     VALUES ('Amit', 'Bhushan', 'imamit.a001@gmail.com');
     ```

   - Verify the record was inserted:

     ```sql
     SELECT * FROM student_details;
     ```

2. **Check the Replication on the Replica Node**:

   - On the replica node, switch to the `postgres` user:

     ```bash
     sudo -u postgres psql
     ```

   - List the databases to ensure the `students_db` database has been replicated:

     ```sql
     \l
     ```

   - Connect to the `students_db`:

     ```sql
     \c students_db;
     ```

   - Query the `student_details` table to confirm the data has been replicated:

     ```sql
     SELECT * FROM student_details;
     ```

   - You should see the same data that was inserted on the primary node, confirming that the replication is working correctly.


