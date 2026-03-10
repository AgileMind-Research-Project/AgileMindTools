from sqlalchemy import create_engine, text
import logging
import pandas as pd
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


def create_database_connection(schema):
    """
    Create a database connection using credentials from environment variables.

    Args:
        schema (str): Database schema/name.

    Returns:
        engine: SQLAlchemy engine object
    """
    try:
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        db_name = schema
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')

        if not all([db_host, db_port, db_name, db_user, db_password]):
            raise ValueError("Missing required database credentials in .env file")

        connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_string, echo=False)
        logging.info(f"Database connection created successfully for schema: {db_name}")
        return engine

    except Exception as exception:
        logging.error(f'Error in connecting to database: {str(exception)}')
        raise


def execute_query(sql_statement, params, schema):
    """Execute a write query (INSERT/UPDATE/DELETE)."""
    connection = create_database_connection(schema)
    try:
        with connection.connect() as conn:
            conn.execute(text(sql_statement), params)
            conn.commit()
        return True
    except Exception as exception:
        logging.error(('Error in executing sql query:', sql_statement, str(exception)))
        return False


def read_from_mysql_with_params(sql_statement, parameters, schema):
    """Execute a read query and return a pandas DataFrame."""
    connection = create_database_connection(schema)
    try:
        return pd.read_sql(sql_statement, connection, params=parameters)
    except Exception as exception:
        logging.error(('Error in executing sql statement:', sql_statement, str(exception)))
        return pd.DataFrame()
