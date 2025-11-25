import socket
import json

HOST = "127.0.0.1"
PORT = 5000
TIMEOUT_SECONDS = 5  # timeout réseau

def _call(method, params=None):
    """
    Envoie une requête JSON-RPC au serveur (tcp) avec gestion
    du timeout et des erreurs réseau.
    """
    if params is None:
        params = {}

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    data = json.dumps(payload) + "\n"

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT_SECONDS)

    try:
        s.connect((HOST, PORT))
        s.sendall(data.encode("utf-8"))

        buffer = s.recv(4096).decode("utf-8")

    except socket.timeout:
        # Timeout : le serveur ne répond pas à temps
        raise Exception("Erreur réseau : timeout lors de l'appel RPC")

    except OSError as e:
        # Problème de connexion ou autre erreur réseau
        raise Exception(f"Erreur réseau lors de l'appel RPC : {e}")

    finally:
        s.close()

    # Traitement de la réponse JSON-RPC
    response = json.loads(buffer)
    if "error" in response:
        raise Exception(f"Erreur RPC : {response['error']}")

    return response.get("result")

def marquer_presence(etudiant_id, seance_id, statut):
    return _call("marquer_presence", {
        "etudiant_id": etudiant_id,
        "seance_id": seance_id,
        "statut": statut
    })

def get_presences(etudiant_id):
    return _call("get_presences", {
        "etudiant_id": etudiant_id
    })

def valider_seance(seance_id, validation: bool):
    return _call("valider_seance", {
        "seance_id": seance_id,
        "validation": validation
    })

