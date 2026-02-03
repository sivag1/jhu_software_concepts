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

Run the data loading script to create the table and insert data and then run the query. The query also includes the two additional queries I am curious about.

```bash
python load_data.py
python query_data.py
```

## How to run the Webpage

Use the command below

```bash
python app.py
```

Open your browser and navigate to `http://localhost:5000`.

The page has two buttons. The Pull Data button loads any new data from the Grad Cafe. It does all the steps we did in Module 2, sequentially, and then load the new records to the DB.

The Update Analysis simply refreshes the page to reload the query results.

A screenshot of how the page looks like is included.