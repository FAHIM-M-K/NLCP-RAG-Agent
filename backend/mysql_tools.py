import os
from dotenv import load_dotenv
import mysql.connector
from pymongo import MongoClient
import json
from datetime import date
from decimal import Decimal

from mcp.server.fastmcp import FastMCP


# load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME") 

CA_CERT_CONTENT = os.getenv("DB_CA_CERT")
MYSQL_SSL_CA_PATH = "ca.pem"

if CA_CERT_CONTENT:
    with open(MYSQL_SSL_CA_PATH, "w") as f:
        f.write(CA_CERT_CONTENT.replace('\\n', '\n'))
    print("Created ca.pem from environment variable.")
else:
    print("DB_CA_CERT not found in env, looking for local ca.pem file.")

mcp_server = FastMCP("MySQL_Tools")

def _get_mysql_connection():

    if not all([MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD]):
        raise ValueError("MySQL credentials not fully set in environment variables.")
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=int(MYSQL_PORT),
            database=MYSQL_DATABASE,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            ssl_ca=MYSQL_SSL_CA_PATH
        )
        return conn
    except mysql.connector.Error as err:
        raise ConnectionError(f"Failed to connect to MySQL: {err}")
    except ValueError:
        raise ValueError("MYSQL_PORT must be a valid integer.")

def _get_mongodb_connection():

    if not all([MONGO_URI, MONGO_DB_NAME]):
        raise ValueError("MongoDB credentials not fully set in environment variables.")
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        return client, db
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")

@mcp_server.tool()
def get_top_n_portfolios(limit: float = 5.0) -> str: 
    """
    Retrieves the top N portfolios based on their latest portfolio value.
    """
    conn = None
    try:
        conn = _get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        int_limit = int(limit) 

        query = """
        SELECT client_id, portfolio_value
        FROM client_portfolios
        ORDER BY portfolio_value DESC
        LIMIT %s;
        """
        cursor.execute(query, (int_limit,))
        results = cursor.fetchall()

        for row in results:
            if 'portfolio_value' in row and isinstance(row['portfolio_value'], Decimal):
                row['portfolio_value'] = float(row['portfolio_value'])

        return json.dumps(results, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "Database connection failed."})
    except mysql.connector.Error as err:
        return json.dumps({"error": str(err), "message": f"Failed to retrieve top N portfolios from MySQL. Database Error: {err}"})
    except Exception as e:
        return json.dumps({"error": str(e), "message": "An unexpected error occurred while fetching top portfolios."})
    finally:
        if conn:
            conn.close()


@mcp_server.tool()
def get_portfolio_values_by_relationship_manager(relationship_manager_name: str) -> str:
    """
    Aggregates the total latest portfolio value for clients managed by a specific
    relationship manager by cross-referencing with MongoDB client data and MySQL portfolio data.
    """
    mongo_client = None
    mysql_conn = None
    try:
        mongo_client, db = _get_mongodb_connection()
        clients_collection = db.clients
        
        rm_clients = clients_collection.find(
            {"relationship_manager": {"$regex": f"^{relationship_manager_name}$", "$options": "i"}},
            {"client_id": 1, "_id": 0}
        )
        client_ids = [doc["client_id"] for doc in rm_clients if "client_id" in doc]

        if not client_ids:
            return json.dumps({
                "relationship_manager": relationship_manager_name,
                "total_portfolio_value": 0.0,
                "message": f"No clients found for relationship manager '{relationship_manager_name}'."
            })


        mysql_conn = _get_mysql_connection()
        cursor = mysql_conn.cursor(dictionary=True)

        placeholders = ', '.join(['%s'] * len(client_ids))
        query = f"""
        SELECT client_id, portfolio_value
        FROM client_portfolios
        WHERE client_id IN ({placeholders});
        """
        cursor.execute(query, tuple(client_ids))
        mysql_results = cursor.fetchall()

        total_portfolio_value = Decimal(0)
        for row in mysql_results:
            if 'portfolio_value' in row and isinstance(row['portfolio_value'], Decimal):
                total_portfolio_value += row['portfolio_value']

        return json.dumps({
            "relationship_manager": relationship_manager_name,
            "total_portfolio_value": float(total_portfolio_value)
        }, indent=2)

    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "Database connection failed (MongoDB or MySQL)."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": f"Failed to get portfolio values for RM {relationship_manager_name}. Error: {e}"})
    finally:
        if mysql_conn:
            mysql_conn.close()
        if mongo_client:
            mongo_client.close()


@mcp_server.tool()
def get_client_transactions(client_id: str, start_date: str = None, end_date: str = None) -> str:

    conn = None
    try:
        conn = _get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM transactions WHERE client_id = %s"
        params = [client_id]

        if start_date and end_date:
            query += " AND transaction_date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif start_date:
            query += " AND transaction_date >= %s"
            params.append(start_date)
        elif end_date:
            query += " AND transaction_date <= %s"
            params.append(end_date)

        query += " ORDER BY transaction_date DESC;"

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        for row in results:
            if 'transaction_date' in row and isinstance(row['transaction_date'], date):
                row['transaction_date'] = row['transaction_date'].isoformat()

        return json.dumps(results, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "Database connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": f"Failed to retrieve transactions for client {client_id}. Error: {e}"})
    finally:
        if conn:
            conn.close()

@mcp_server.tool()
def get_stock_holders_for_stock(stock_symbol: str) -> str:
    """
    Identifies which clients hold a specific stock based on their transaction data (buy transactions).
    Aggregates the total quantity bought by each client for the given stock.
    """
    conn = None
    try:
        conn = _get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT client_id, stock_symbol, SUM(quantity) AS total_quantity
        FROM transactions
        WHERE transaction_type = 'buy' AND LOWER(stock_symbol) = LOWER(%s)
        GROUP BY client_id, stock_symbol
        ORDER BY total_quantity DESC;
        """
        cursor.execute(query, (stock_symbol,))
        results = cursor.fetchall()
        return json.dumps(results, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "Database connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": f"Failed to get holders for stock {stock_symbol}. Error: {e}"})
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print(f"Starting {mcp_server.name} MCP Server...")
    mcp_server.run(transport="stdio")

