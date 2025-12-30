import requests
import json

RPC_URL = "http://127.0.0.1:5000/"

def call_rpc(method, params):
    """Fonction générique pour appeler le serveur RPC"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    
    try:
        response = requests.post(RPC_URL, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"status": "error", "message": f"Erreur réseau : {str(e)}"}

    try:
        data = response.json()
    except json.JSONDecodeError:
        return {"status": "error", "message": "Réponse invalide du serveur"}

    # Gestion des erreurs JSON-RPC
    if "error" in data:
        error_msg = data["error"].get("message", "Erreur serveur")
        return {"status": "error", "message": error_msg}
    
    # Si succès
    if "result" in data:
        result = data["result"]
        # Vérifier si c'est un objet Success de jsonrpcserver
        if isinstance(result, dict) and "value" in result:
            return result["value"]
        return result
    
    return {"status": "error", "message": "Réponse inattendue du serveur"}

# =========================================
# FONCTIONS CLIENT
# =========================================

def login_etudiant(email, mot_de_passe):
    """Connexion étudiant"""
    return call_rpc("login_etudiant", {"email": email, "mot_de_passe": mot_de_passe})

def get_info_etudiant(etudiant_id):
    """Récupère les informations complètes d'un étudiant"""
    return call_rpc("get_info_etudiant", {"etudiant_id": etudiant_id})

def get_groupes_etudiant(etudiant_id):
    """Récupère les groupes d'un étudiant"""
    return call_rpc("get_groupes_etudiant", {"etudiant_id": etudiant_id})

def get_seances_aujourdhui(etudiant_id):
    """Récupère les séances d'aujourd'hui pour un étudiant"""
    return call_rpc("get_seances_aujourdhui", {"etudiant_id": etudiant_id})

def get_seances_semaine(etudiant_id):
    """Récupère les séances de la semaine pour un étudiant"""
    return call_rpc("get_seances_semaine", {"etudiant_id": etudiant_id})

def get_absences_etudiant(etudiant_id):
    """Récupère les absences d'un étudiant"""
    return call_rpc("get_absences_etudiant", {"etudiant_id": etudiant_id})

def get_notifications_etudiant(etudiant_id, non_lues_seulement=False):
    """Récupère les notifications d'un étudiant"""
    params = {"etudiant_id": etudiant_id}
    if non_lues_seulement:
        params["non_lues_seulement"] = non_lues_seulement
    return call_rpc("get_notifications_etudiant", params)

def marquer_notifications_lues(etudiant_id):
    """Marque toutes les notifications comme lues"""
    return call_rpc("marquer_notifications_lues", {"etudiant_id": etudiant_id})

def get_statistiques_presence(etudiant_id):
    """Récupère les statistiques de présence d'un étudiant"""
    return call_rpc("get_statistiques_presence", {"etudiant_id": etudiant_id})

def get_presences_etudiant(etudiant_id, statut=None):
    """Récupère toutes les présences d'un étudiant avec filtre optionnel"""
    params = {"etudiant_id": etudiant_id}
    if statut:
        params["statut"] = statut
    return call_rpc("get_presences_etudiant", params)

def ajouter_justification_absence(etudiant_id, presence_id, justification):
    """Ajoute une justification à une absence"""
    return call_rpc("ajouter_justification_absence", {
        "etudiant_id": etudiant_id,
        "presence_id": presence_id,
        "justification": justification
    })