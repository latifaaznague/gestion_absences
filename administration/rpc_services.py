# Dans rpc_services.py
from services.rpc_client import JsonRpcClient

STUDENT_RPC = JsonRpcClient(
    "http://127.0.0.1:8001/rpc",
    headers={"Authorization": "Bearer mon_super_token_12345"}
)

COURSE_RPC = JsonRpcClient(
    "http://127.0.0.1:8001/rpc",
    headers={"Authorization": "Bearer mon_super_token_12345"}
)

PLANNING_RPC = JsonRpcClient(
    "http://127.0.0.1:8001/rpc",
    headers={"Authorization": "Bearer mon_super_token_12345"}
)