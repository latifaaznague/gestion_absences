# services/rpc_services.py
from .rpc_client import JsonRpcClient

# URL de base
RPC_BASE_URL = "http://127.0.0.1:8001/rpc"

# Token d'authentification
RPC_TOKEN = "mon_super_token_12345"

# Headers communs
COMMON_HEADERS = {
    "Authorization": f"Bearer {RPC_TOKEN}",
    "Content-Type": "application/json"
}

# Clients pour chaque module
STUDENT_RPC = JsonRpcClient(RPC_BASE_URL, COMMON_HEADERS)
COURSE_RPC = JsonRpcClient(RPC_BASE_URL, COMMON_HEADERS)
PLANNING_RPC = JsonRpcClient(RPC_BASE_URL, COMMON_HEADERS)
AUTH_RPC = JsonRpcClient(RPC_BASE_URL, COMMON_HEADERS)