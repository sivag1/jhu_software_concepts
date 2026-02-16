Testing Guide
=============

Information on how to test the application effectively.

Running Marked Tests
--------------------
Tests can be categorized by markers. To run a specific subset of tests, use:

.. code-block:: bash

   pytest -m <marker_name>

Expected Selectors
------------------
The integration tests expect specific HTML selectors to be present in the DOM.

Test Doubles & Fixtures
-----------------------
The test suite utilizes fixtures for setup/teardown and test doubles (mocks) to isolate components during testing.