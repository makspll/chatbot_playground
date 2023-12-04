
import logging
import os
from dotenv import load_dotenv
import os
from dotenv import load_dotenv
from io import StringIO
import mysql.connector


def create_mysql_connection() -> mysql.connector.connection.MySQLConnection:
    # Get MySQL credentials from .env file
    mysql_host = os.getenv("DB_HOST")
    mysql_user = os.getenv("DB_USERNAME")
    mysql_password = os.getenv("DB_PASSWORD")
    mysql_database = os.getenv("MYSQL_DATABASE")
    logging.info(f"Connecting to mysql: host: {mysql_host}, user: {mysql_user}, database: {mysql_database}")
    # Create MySQL connection object
    connection = mysql.connector.connect(
        host=mysql_host,
        user=mysql_user,
        password=mysql_password,
        database=mysql_database,
    )

    return connection




def run_query_many(query: str, max_rows: int, connection: mysql.connector.connection.MySQLConnection) -> str:
    """ Runs a query expecting muliple rows as a result and returns the result as a string"""
    logging.info("Starting cursor")
    cursor = connection.cursor()
    logging.info("Executing query: %s", query)
    # Execute the query
    cursor.execute(query)

    # Fetch the results
    logging.info("Fetching results one by one")
    results = cursor.fetchmany(max_rows)

    # Convert results to string using StringBuilder
    result_str = StringIO()
    
    for i, row in enumerate(results):
        if i >= max_rows:
            break
        result_str.write(str(row) + "\n")

    result_str = result_str.getvalue()
    logging.info("Built result: %s", result_str)

    # Close the cursor
    cursor.close()
    return result_str


