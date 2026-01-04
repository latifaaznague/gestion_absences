import json
import urllib.request

url = "http://127.0.0.1:8001/rpc"
payload = {
    "jsonrpc": "2.0",
    "method": "auth.login",
    "params": {"email": "admin@uiz.ac.ma", "motDePasse": "admin123"},
    "id": 1
}

try:
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode("utf-8"),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as response:
        print("RÉPONSE DU SERVEUR :", response.read().decode())
except Exception as e:
    print("ERREUR DE CONNEXION :", e)