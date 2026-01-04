import requests
import json

RPC_SERVER_URL = "http://127.0.0.1:5001"  # Port 5001 pour les professeurs

def call_rpc_method(method, params=None):
    """Fonction générique pour appeler une méthode RPC"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": 1
    }
    
    try:
        response = requests.post(
            RPC_SERVER_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erreur de connexion au serveur RPC: {str(e)}")

def login_professeur(email, mot_de_passe):
    """Connexion d'un professeur"""
    try:
        result = call_rpc_method("login_professeur", [email, mot_de_passe])
        
        if "result" in result:
            return result["result"]
        elif "error" in result:
            return {
                "status": "error",
                "message": result["error"]["message"]
            }
        else:
            return {
                "status": "error",
                "message": "Réponse inattendue du serveur RPC"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erreur de connexion au serveur RPC: {str(e)}"
        }