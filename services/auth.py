# services/auth.py
import uuid
import hashlib
import binascii
import os
import requests
from services.db import get_conn

TOKENS = {}
RPC_SERVERS = {
    "admin": "http://127.0.0.1:8001/rpc",
    "etudiant": "http://127.0.0.1:5000/"
}

def hash_password(password, salt=None):
    """Hash un mot de passe avec pbkdf2_sha256 (compatible Django)"""
    if salt is None:
        salt = os.urandom(16).hex()
    
    hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        1000000
    )
    hash_hex = binascii.hexlify(hash).decode('utf-8')
    return f"pbkdf2_sha256$1000000${salt}${hash_hex}"

def verify_password(password, hashed):
    """Vérifie si un mot de passe correspond au hash"""
    try:
        if not password or not hashed:
            return False
            
        if not hashed.startswith('pbkdf2_sha256$'):
            return password == hashed
        
        parts = hashed.split('$')
        if len(parts) != 4:
            return False
            
        algorithm, iterations, salt, stored_hash = parts
        iterations = int(iterations)
        
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        new_hash = binascii.hexlify(hash_obj).decode('utf-8')
        
        return stored_hash == new_hash
        
    except Exception:
        return False

def login(p):
    email = (p.get("email") or "").strip()
    password = (p.get("motDePasse") or "").strip()

    if not email or not password:
        raise ValueError("Email ou mot de passe manquant")

    conn = get_conn()
    cur = conn.cursor()
    
    # Récupérer l'utilisateur AVEC le type
    cur.execute("""
        SELECT id, type_utilisateur, nom, prenom, email, mot_de_passe, date_creation
        FROM utilisateur
        WHERE TRIM(email)=%s
    """, (email,))
    
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise ValueError("Email ou mot de passe incorrect")
    
    # Vérifier le mot de passe
    user_id, role, nom, prenom, user_email, hashed_password, date_creation = row
    
    if not verify_password(password, hashed_password):
        raise ValueError("Email ou mot de passe incorrect")

    # Générer un token
    token = str(uuid.uuid4())
    
    # Stocker dans TOKENS
    TOKENS[token] = {
        "user_id": user_id, 
        "role": role,
        "nom": nom,
        "prenom": prenom,
        "email": user_email
    }

    # Retourner toutes les informations
    return {
        "token": token, 
        "role": role,
        "user_id": user_id,
        "nom": nom,
        "prenom": prenom,
        "email": user_email,
        "type_utilisateur": role,
        "date_creation": str(date_creation) if date_creation else None
    }

def logout(p):
    token = p.get("token")
    if token in TOKENS:
        del TOKENS[token]
    return True

def check_token(token, roles=None):
    """Vérifie le token pour l'authentification"""
    if token in TOKENS:
        if roles:
            user_role = TOKENS[token]["role"]
            if user_role not in roles:
                raise ValueError("Unauthorized")
        return True
    
    raise ValueError("Unauthorized")

def get_user_by_token(token):
    """Récupère l'utilisateur à partir du token"""
    return TOKENS.get(token)