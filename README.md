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
2. [Installation](#installation)
3. [Repository Structure](#repository-structure)
4. [Usage](#usage)
    - [Running the API](#running-the-api)
    - [Deploying Infrastructure](#deploying-infrastructure)
5. [API Endpoints](#api-endpoints)
6. [License](#license)

---

## Requirements

Before getting started, ensure that you have the following tools installed on your local or remote server:

- Python 3.x
- [Terraform](https://www.terraform.io/downloads)
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
- AWS credentials configured in your environment (for example using `aws configure`)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/bhushan-amit/postgres-infra-api.git
cd postgres-infra-api
```

### 2. Install Python Requirements

The Flask API requires some Python dependencies to be installed.

```bash
cd api
pip install -r requirements.txt
```

### 3. Install Terraform and Ansible

Ensure Terraform and Ansible are properly installed and available on your system.

- Terraform installation: [Terraform Install Guide](https://developer.hashicorp.com/terraform/downloads)
- Ansible installation: [Ansible Install Guide](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

## Repository Structure

```bash
postgres-infra-api/
├── api/                    # Flask API application
│   ├── app.py              # Flask application
│   ├── requirements.txt    # Python requirements
├── ansible-postgres/        # Ansible playbooks for PostgreSQL setup
│   ├── playbooks/
│   ├── inventory/           # Generated dynamically
├── terraform/               # Terraform scripts for AWS infrastructure
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars
│   ├── generate_inventory.sh
└── README.md
```

## Usage

### 1. Configure Terraform Variables

Edit the `terraform/terraform.tfvars` file to set up your AWS settings:

Here you can specify instance types and the number of replicas:

```hcl
region = "ap-south-1"
instance_type = "t2.micro"
replica_count = 2

```

### 2. Running the API

To start the Flask API, navigate to the `api/` directory and run the following:

```bash
python app.py
```

The API will start on `http://127.0.0.1:5000` by default.

### 3. Deploying Infrastructure

You can now use the API to deploy the infrastructure. The API supports POST requests to create the infrastructure dynamically based on the number of replicas and instance type.

### Example API Request

Use `curl` or any API testing tool to send a POST request to the `/setup` endpoint to deploy the infrastructure.

```bash
curl -X POST http://127.0.0.1:5000/setup -H "Content-Type: application/json" -d '{
  "instance_type": "t2.micro",
  "replica_count": 2
}'
```

This will:

1. Initialize Terraform.
2. Deploy AWS infrastructure for PostgreSQL (Primary DB + Replicas).
3. Dynamically generate an Ansible inventory.
4. Run Ansible playbooks to configure the PostgreSQL instances.

### 4. Updating Infrastructure

To change the number of replicas or update any other settings, simply modify the parameters in the API request and send another POST request.

## API Endpoints

### `/setup` (POST)

This endpoint deploys the PostgreSQL infrastructure on AWS and configures the instances using Ansible.

- **Request Body**:
  - `instance_type`: (string) AWS instance type (e.g., `t2.micro`)
  - `replica_count`: (int) Number of PostgreSQL replica instances to deploy

- **Response**: Success or failure message with logs.


## Troubleshooting

1. **SSH access to EC2 instances**: Ensure you have the correct SSH key file configured and accessible.
2. **Environment variables**: If environment variables aren't applied, double-check that they are correctly set before running Terraform or Ansible.

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
     VALUES ('Arthur', 'Spencer', 'arthurspencer@gmail.com');
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

