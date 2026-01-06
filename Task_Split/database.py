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
        schema (str, optional): Database schema/name. If not provided, uses 'agilemind_db'
    
    Returns:
        engine: SQLAlchemy engine object
    """
    try:
        # Get database credentials from environment variables
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        db_name = schema 
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        
        # Validate that all credentials are present
        if not all([db_host, db_port, db_name, db_user, db_password]):
            raise ValueError("Missing required database credentials in .env file")
        
        # Create connection string
        connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Create and return engine
        engine = create_engine(connection_string, echo=False)
        logging.info(f"Database connection created successfully for schema: {db_name}")
        return engine
        
    except Exception as exception:
        logging.error(f'Error in connecting to database: {str(exception)}')
        raise

def execute_query(sql_statement,params,schema):
    connection = create_database_connection(schema)
    try:
        with connection.connect() as conn:
            conn.execute(text(sql_statement), params)
            print(conn.commit())
        return True
    except Exception as exception:
        logging.error(('Error in executing sql query :',sql_statement, str(exception)))
        return False
    
def read_from_mysql_with_params(sql_statement,parameters,schema):
    connection = create_database_connection(schema)
    try:
        return pd.read_sql((sql_statement), connection, params=parameters)
    except Exception as exception:
        logging.error(('Error in executing sql statement :',sql_statement, str(exception)))
        return pd. DataFrame()
    
def write_to_mysql(table,dataframe,datatypes,schema,method):
    connection = create_database_connection(schema)
    try:
        dataframe.to_sql(table, con=connection, if_exists=method, index=False, dtype=datatypes)
        print(f"Data written to '{table}' table successfully.")
    except Exception as exception:
        print(exception)
        logging.error(('Error in writing to database :', str(exception)))
        return "failed db",500    