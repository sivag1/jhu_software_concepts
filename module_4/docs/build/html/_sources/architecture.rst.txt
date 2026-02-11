Architecture
============

This section describes the high-level architecture of the Grad Cafe App.

Web Layer
---------
The Web layer is built using Flask. It handles HTTP requests, defines routes, and serves the frontend interface to the user.

ETL Layer
---------
The ETL (Extract, Transform, Load) layer is responsible for data ingestion.
It scrapes data from external sources, cleans/normalizes it, and prepares it for storage.

DB Layer
--------
The Database layer manages the persistence of data. It handles the database connection, schema definitions, and query execution.