# rpc_client.py
import json
import requests
from typing import Any, Dict, Optional

class RpcError(Exception):
    pass

class JsonRpcClient:
    def __init__(self, url: str, headers: Optional[Dict] = None):
        self.url = url
        self.headers = headers or {}
        self.token = ""
        if self.headers:
            auth_header = self.headers.get("Authorization", "")
            if isinstance(auth_header, str):
                self.token = auth_header.replace("Bearer ", "")
    
    def call(self, method: str, params: Dict = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        if self.token and method not in ["auth.login", "auth.logout"]:
            payload["params"]["_token"] = self.token
        
        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise RpcError(f"RPC Error: {result['error']}")
            return result.get("result", {})
            
        except requests.exceptions.RequestException as e:
            raise RpcError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise RpcError(f"Invalid JSON response: {str(e)}")

# ============================================================================
# CONFIGURATION DES SERVEURS
# ============================================================================

# CORRECTION : Deux serveurs différents
ETUDIANT_SERVER_URL = "http://127.0.0.1:5000/"   # Serveur étudiant Flask
ADMIN_SERVER_URL = "http://127.0.0.1:8001/rpc"  # Serveur admin (si vous l'avez)

# Token par défaut
DEFAULT_TOKEN = "mon_super_token_12345"
DEFAULT_HEADERS = {"Authorization": f"Bearer {DEFAULT_TOKEN}"}

# Clients pour les différents serveurs
_etudiant_client = JsonRpcClient(ETUDIANT_SERVER_URL, {})  # Pas besoin de headers pour étudiant
_admin_client = JsonRpcClient(ADMIN_SERVER_URL, DEFAULT_HEADERS)

# ============================================================================
# FONCTIONS POUR LE SERVEUR ÉTUDIANT (PORT 5000)
# ============================================================================

def call_etudiant_rpc(method: str, params: Dict = None) -> Any:
    """Appelle le serveur étudiant (Flask sur port 5000)"""
    try:
        # Pas besoin de token pour les méthodes étudiantes
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        response = requests.post(ETUDIANT_SERVER_URL, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Gestion de la réponse de jsonrpcserver
        if "result" in data:
            result = data["result"]
            # jsonrpcserver retourne {"value": {...}}
            if isinstance(result, dict) and "value" in result:
                return result["value"]
            return result
        elif "error" in data:
            return {"status": "error", "message": data["error"].get("message", "Erreur serveur")}
        
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": f"Le serveur étudiant n'est pas disponible à {ETUDIANT_SERVER_URL}"}
    except Exception as e:
        return {"status": "error", "message": f"Erreur: {str(e)}"}
    
    return {"status": "error", "message": "Réponse inattendue"}

# ============================================================================
# FONCTIONS ÉTUDIANT (UTILISENT LE SERVEUR ÉTUDIANT)
# ============================================================================

def login_etudiant(email, mot_de_passe):
    """Connexion étudiant - utilise le serveur étudiant"""
    return call_etudiant_rpc("login_etudiant", {
        "email": email,
        "mot_de_passe": mot_de_passe
    })

def get_info_etudiant(etudiant_id):
    """Récupère les informations complètes d'un étudiant"""
    return call_etudiant_rpc("get_info_etudiant", {"etudiant_id": etudiant_id})

def get_groupes_etudiant(etudiant_id):
    """Récupère les groupes d'un étudiant"""
    return call_etudiant_rpc("get_groupes_etudiant", {"etudiant_id": etudiant_id})

def get_seances_aujourdhui(etudiant_id):
    """Récupère les séances d'aujourd'hui pour un étudiant"""
    return call_etudiant_rpc("get_seances_aujourdhui", {"etudiant_id": etudiant_id})

def get_seances_semaine(etudiant_id):
    """Récupère les séances de la semaine pour un étudiant"""
    return call_etudiant_rpc("get_seances_semaine", {"etudiant_id": etudiant_id})

def get_absences_etudiant(etudiant_id):
    """Récupère les absences d'un étudiant"""
    return call_etudiant_rpc("get_absences_etudiant", {"etudiant_id": etudiant_id})

def get_notifications_etudiant(etudiant_id, non_lues_seulement=False):
    """Récupère les notifications d'un étudiant"""
    params = {"etudiant_id": etudiant_id}
    if non_lues_seulement:
        params["non_lues_seulement"] = non_lues_seulement
    return call_etudiant_rpc("get_notifications_etudiant", params)

def marquer_notifications_lues(etudiant_id):
    """Marque toutes les notifications comme lues"""
    return call_etudiant_rpc("marquer_notifications_lues", {"etudiant_id": etudiant_id})

def get_statistiques_presence(etudiant_id):
    """Récupère les statistiques de présence d'un étudiant"""
    return call_etudiant_rpc("get_statistiques_presence", {"etudiant_id": etudiant_id})

def get_presences_etudiant(etudiant_id, statut=None):
    """Récupère toutes les présences d'un étudiant avec filtre optionnel"""
    params = {"etudiant_id": etudiant_id}
    if statut:
        params["statut"] = statut
    return call_etudiant_rpc("get_presences_etudiant", params)

def ajouter_justification_absence(etudiant_id, presence_id, justification):
    """Ajoute une justification à une absence"""
    return call_etudiant_rpc("ajouter_justification_absence", {
        "etudiant_id": etudiant_id,
        "presence_id": presence_id,
        "justification": justification
    })

# ============================================================================
# FONCTIONS POUR LE SERVEUR ADMIN (PORT 8001) - SI BESOIN
# ============================================================================

def presence_call(method: str, params: Dict = None) -> Any:
    return _admin_client.call(method, params)

def marquer_presence(etudiant_id: int, seance_id: int, present: bool = True):
    return _admin_client.call("presence.mark", {
        "etudiantId": etudiant_id,
        "seanceId": seance_id,
        "present": present,
    })

def get_presences(etudiant_id: int):
    return _admin_client.call("presence.listByStudent", {"etudiantId": etudiant_id})

def valider_seance(seance_id: int):
    return _admin_client.call("seance.validate", {"seanceId": seance_id})

def get_dashboard_stats():
    return _admin_client.call("stats.dashboard")

# ============================================================================
# FONCTION DE TEST
# ============================================================================

def test_etudiant_server():
    """Teste si le serveur étudiant fonctionne"""
    print("Test du serveur étudiant...")
    
    # Test de santé
    try:
        response = requests.get(f"{ETUDIANT_SERVER_URL}health", timeout=5)
        print(f"✓ Health check: {response.status_code}")
        print(f"  Réponse: {response.json()}")
    except Exception as e:
        print(f"✗ Health check échoué: {e}")
        return False
    
    # Test de login avec des données de test
    print("\nTest de login_etudiant...")
    result = login_etudiant("test@example.com", "test123")
    print(f"Résultat: {result}")
    
    return True

if __name__ == "__main__":
    # Testez le serveur étudiant
    test_etudiant_server()