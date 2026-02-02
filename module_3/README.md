# Module 3: Data Loading

This module handles the loading of applicant data into a PostgreSQL database.

## Prerequisites

- Python 3.x
- PostgreSQL installed and running locally

## Setup

1.  **Install Dependencies**

    Install the required Python packages using pip:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Configuration**

    Create a `.env` file in the `module_3` directory to store your database credentials. This file is required for the script to connect to your database.

    **Example `.env` content:**
    ```dotenv
    DB_HOST=localhost
    DB_NAME=postgres
    DB_USER=postgres
    DB_PASSWORD=postgres
    ```

## Usage

Run the data loading script to create the table and insert data:

```bash
python load_data.py
```