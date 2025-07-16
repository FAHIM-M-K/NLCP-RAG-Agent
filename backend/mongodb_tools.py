import os
from dotenv import load_dotenv
from pymongo import MongoClient
from mcp.server.fastmcp import FastMCP

import json

# load .env
# load_dotenv()


# Add these lines for debugging:
print(f"DEBUG: Reading MYSQL_HOST: '{os.getenv('MYSQL_HOST')}'")
print(f"DEBUG: Reading MYSQL_PORT: '{os.getenv('MYSQL_PORT')}'")
print(f"DEBUG: Reading MYSQL_DATABASE: '{os.getenv('MYSQL_DATABASE')}'")
print(f"DEBUG: Reading MYSQL_USER: '{os.getenv('MYSQL_USER')}'")
# Only print first few chars of password or 'None'


MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

mcp_server = FastMCP("MongoDB_Tools")

def _get_mongo_collection():
    if not MONGO_URI:
        raise ValueError("MONGO_URI not found in environment variables.")
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        return db.clients, client 
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")

@mcp_server.tool()
def get_client_profile_by_name(client_name: str) -> str:
    """
    Retrieves a client's detailed profile from MongoDB based on their full name.
    This includes name, address, risk appetite, investment preferences, relationship manager,
    and initial portfolio value.
    """
    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        client_data = collection.find_one({"name": {"$regex": client_name, "$options": "i"}}, {"_id": 0})
        if client_data:
            return json.dumps(client_data, indent=2)
        else:
            return json.dumps({})
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": "Failed to retrieve client profile."})
    finally:
        if client_conn:
            client_conn.close()


@mcp_server.tool()
def get_clients_by_profession(profession: str) -> str:
    """
    Retrieves a list of client names and their associated initial portfolio values
    from MongoDB who are identified by a specific profession (e.g., 'Actor', 'Sportsperson').
    The search is case-insensitive and checks for profession within the client's name.
    """
    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        search_pattern = f"\\b{profession}\\b" 
        
        clients_cursor = collection.find(
            {"name": {"$regex": search_pattern, "$options": "i"}},
            {"name": 1, "initial_portfolio_value_crores": 1, "client_id": 1, "_id": 0}
        )
        clients_list = list(clients_cursor)
        return json.dumps(clients_list, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": "Failed to retrieve clients by profession."})
    finally:
        if client_conn:
            client_conn.close()


@mcp_server.tool()
def get_clients_by_risk_appetite(risk_appetite_level: str) -> str:
    """
    Retrieves a list of client names and their initial portfolio values from MongoDB
    based on their risk appetite level, 'High', 'Medium', or 'Low', return JSON string(always for every tool)
    """
    if risk_appetite_level not in ['High', 'Medium', 'Low']:
        return json.dumps({"error": "Invalid risk appetite level. Must be 'High', 'Medium', or 'Low'."})

    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        clients_cursor = collection.find(
            {"risk_appetite": risk_appetite_level},
            {"name": 1, "initial_portfolio_value_crores": 1, "client_id": 1, "_id": 0}
        )
        clients_list = list(clients_cursor)
        return json.dumps(clients_list, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": "Failed to retrieve clients by risk appetite."})
    finally:
        if client_conn:
            client_conn.close()

@mcp_server.tool()
def get_clients_by_investment_preference(preference: str) -> str:
    """
    Retrieves a list of client names and their risk appetite who have a specific investment preference.
    """
    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        clients_cursor = collection.find(
            {"investment_preferences": {"$regex": preference, "$options": "i"}},
            {"name": 1, "risk_appetite": 1, "client_id": 1, "_id": 0}
        )
        clients_list = list(clients_cursor)
        return json.dumps(clients_list, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": "Failed to retrieve clients by investment preference."})
    finally:
        if client_conn:
            client_conn.close()

@mcp_server.tool()
def get_top_relationship_managers() -> str:
    """
    Analyzes the MongoDB clients collection to identify relationship managers and the number of
    clients they manage, sorted by client count in descending order.
    """
    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        pipeline = [
            {"$group": {"_id": "$relationship_manager", "client_count": {"$sum": 1}}},
            {"$sort": {"client_count": -1}}
        ]
        managers_data = list(collection.aggregate(pipeline))
        return json.dumps(managers_data, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": "Failed to retrieve top relationship managers."})
    finally:
        if client_conn:
            client_conn.close()


@mcp_server.tool()
def get_client_profile_by_id(client_id: str) -> str:
    """
    Retrieves the full client profile from MongoDB using their unique client ID.
    """
    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        client_data = collection.find_one(
            {"client_id": client_id},
            {"_id": 0} # Exclude the MongoDB default _id field
        )
        if client_data:
            return json.dumps(client_data, indent=2)
        else:
            return json.dumps({"message": f"Client with ID {client_id} not found."})
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": f"Failed to retrieve client profile for ID {client_id}."})
    finally:
        if client_conn:
            client_conn.close()

@mcp_server.tool()
def get_client_ids_by_relationship_manager(relationship_manager_name: str) -> str:
    """
    Retrieves a list of client IDs who are managed by a specific relationship manager from MongoDB.
    """
    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        clients_cursor = collection.find(
            {"relationship_manager": {"$regex": relationship_manager_name, "$options": "i"}},
            {"client_id": 1, "_id": 0} #only return client id
        )
        client_ids = [doc['client_id'] for doc in list(clients_cursor) if 'client_id' in doc]
        return json.dumps(client_ids, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        return json.dumps({"error": str(e), "message": f"Failed to retrieve client IDs for RM {relationship_manager_name}."})
    finally:
        if client_conn:
            client_conn.close()

#handle float limit input
@mcp_server.tool()
def get_top_n_clients_by_investment_type_value(investment_type: str, limit: float = 5.0) -> str:
    """
    Retrieves the top N clients with the highest holdings in a specific investment type from MongoDB.
    Uses an aggregation pipeline to filter by investment type, sort by value in descending order, and limit the results.
    Returns a JSON string containing a list of dictionaries, each with 'client_id', 'name', 'risk_appetite', 'investment_type', and 'holding_value_crores'.
    """
    collection, client_conn = None, None
    try:
        collection, client_conn = _get_mongo_collection()
        int_limit = int(limit) 

        pipeline = [
            {
                "$match": {
                    "portfolio_by_preference.type": { "$regex": investment_type, "$options": "i" }
                }
            },
            {
                "$unwind": "$portfolio_by_preference"
            },
            {
                "$match": {
                    "portfolio_by_preference.type": { "$regex": investment_type, "$options": "i" }
                }
            },
            {
                "$sort": { "portfolio_by_preference.value_crores": -1 }
            },
            {
                "$limit": int_limit 
            },
            {
                "$project": {
                    "_id": 0,
                    "client_id": "$client_id",
                    "name": "$name",
                    "risk_appetite": "$risk_appetite",
                    "investment_type": "$portfolio_by_preference.type",
                    "holding_value_crores": "$portfolio_by_preference.value_crores"
                }
            }
        ]
        
        top_clients = list(collection.aggregate(pipeline))
        return json.dumps(top_clients, indent=2)
    except ConnectionError as conn_err:
        return json.dumps({"error": str(conn_err), "message": "MongoDB connection failed."})
    except Exception as e:
        # for debugging
        print(f"DEBUG: Error in get_top_n_clients_by_investment_type_value for '{investment_type}' with limit {limit}: {e}")
        return json.dumps({"error": str(e), "message": f"Failed to retrieve top clients by {investment_type} investment value. Check agent console logs for more details."})
    finally:
        if client_conn:
            client_conn.close()

if __name__ == "__main__":
    print(f"Starting {mcp_server.name} MCP Server...")
    mcp_server.run(transport="stdio")

