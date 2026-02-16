Overview & Setup
================

Instructions on how to set up and run the Grad Cafe App.

Running the App
---------------
To run the application, execute the following command in your terminal:

.. code-block:: bash

   python flask_app.py

Required Environment Variables
------------------------------
The application requires the following environment variables to be set (e.g., in a ``.env`` file):

* ``DATABASE_URL``: The connection string for the database.

Running Tests
-------------
To run the test suite, ensure you have the test dependencies installed and run:

.. code-block:: bash

   pytest