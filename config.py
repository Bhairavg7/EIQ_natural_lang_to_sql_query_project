import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ['DB_PASSWORD'],
    'database': os.environ.get('DB_NAME', 'employees'),
    'port': int(os.environ.get('DB_PORT', 3306))
}

OLLAMA_CONFIG = {
    'url': 'http://localhost:11434/api/generate',
    'model': 'llama3.1',
    'timeout': 180
}

DATABASE_SCHEMA = """
Database: employees

# Table: emp_info
# - emp_id (INT, PRIMARY KEY): Employee ID
# - first_name (VARCHAR(15)): Employee's first name
# - last_name (VARCHAR(15)): Employee's last name
# - age (INT): Employee's age
# - gender (CHAR(1)): Employee's gender (M/F)
# - date_of_joining (DATE): Date when employee joined (YYYY-MM-DD)
# - profession (VARCHAR(10)): Employee's profession

# Table: emp_address
# - emp_id (INT, PRIMARY KEY, FOREIGN KEY): Employee ID (references emp_info.emp_id)
# - permanent_addr (VARCHAR(200)): Permanent address
# - communication_addr (VARCHAR(200)): Communication address
# - zip_code (VARCHAR(10)): ZIP code

# Sample Data:
# emp_info contains:
# - 101, Anjali, Sharma, 29, F, 2021-06-15, Analyst
# - 102, Rohit, Verma, 35, M, 2019-04-10, Manager
# - 103, Sneha, Kumar, 26, F, 2022-01-05, Engineer
# - 104, Amit, Patel, 32, M, 2020-08-20, Designer
# - 105, Priya, Nair, 28, F, 2023-03-01, HR

# Relationships:
# - emp_address.emp_id is linked to emp_info.emp_id
# - Use JOINs when you need data from both tables
# """