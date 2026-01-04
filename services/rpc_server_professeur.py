from flask import Flask, request
from jsonrpcserver import method, dispatch, Error, Success
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import logging
import json

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connexion à PostgreSQL (même base que l'étudiant)
def get_db_connection():
    """Établit une connexion à la base de données"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="gestion_absences",
            user="postgres",
            password="123456",
            port=5432,
            client_encoding='UTF8'
        )
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {repr(e)}")
        raise

def execute_query(query, params=None):
    """Exécute une requête et retourne un seul résultat"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, params or ())
            result = cur.fetchone()
            conn.close()
            return result
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        if conn:
            conn.close()
        raise

def execute_query_all(query, params=None):
    """Exécute une requête et retourne tous les résultats"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, params or ())
            results = cur.fetchall()
            conn.close()
            return results
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        if conn:
            conn.close()
        raise

def execute_update(query, params=None):
    """Exécute une requête de mise à jour"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()
            rows_affected = cur.rowcount
            conn.close()
            return rows_affected
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la mise à jour: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        raise

# =========================================
# FONCTIONS RPC PROFESSEUR
# =========================================

@method
def login_professeur(email: str, mot_de_passe: str):
    """Connexion professeur - Version avec clair (comme étudiants)"""
    logger.info(f"Tentative de connexion professeur pour l'email: {email}")
    
    if not email or not mot_de_passe:
        return Error(code=400, message="Email et mot de passe requis")
    
    try:
        # Vérifier d'abord si l'utilisateur existe
        logger.info(f"Recherche de l'utilisateur avec email: {email}")
        
        user = execute_query(
            "SELECT u.id, u.nom, u.prenom, u.mot_de_passe, u.type_utilisateur "
            "FROM utilisateur u WHERE u.email = %s",
            (email,)
        )

        if not user:
            logger.warning(f"Email non trouvé: {email}")
            return Error(code=401, message="Email incorrect")
        
        logger.info(f"Utilisateur trouvé - Type: {user['type_utilisateur']}")
        
        # Vérifier que c'est un professeur
        if user["type_utilisateur"] != "PROFESSEUR":
            logger.warning(f"L'utilisateur n'est pas un professeur: {user['type_utilisateur']}")
            return Error(code=403, message="Accès réservé aux professeurs")
        
        # Vérifier le mot de passe (en clair, comme dans la base)
        logger.info(f"Comparaison mot de passe - Fourni: {mot_de_passe}, En base: {user['mot_de_passe']}")
        
        if user["mot_de_passe"] != mot_de_passe:
            logger.warning(f"Mot de passe incorrect pour l'email: {email}")
            return Error(code=401, message="Mot de passe incorrect")
        
        # Récupérer les informations spécifiques du professeur
        prof_info = execute_query(
            "SELECT specialite FROM professeur WHERE id = %s",
            (user["id"],)
        )
        
        specialite = prof_info["specialite"] if prof_info else None
        
        logger.info(f"Connexion réussie pour le professeur ID: {user['id']}")
        return Success({
            "status": "success",
            "professeur_id": user["id"],
            "nom": user["nom"],
            "prenom": user["prenom"],
            "specialite": specialite
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {str(e)}", exc_info=True)
        return Error(code=500, message=f"Erreur serveur: {str(e)}")
@method
def get_info_professeur(professeur_id: int):
    """Récupère les informations complètes d'un professeur"""
    logger.info(f"Récupération des informations pour le professeur ID: {professeur_id}")
    
    try:
        query = """
            SELECT 
                p.id as professeur_id,
                p.specialite,
                u.nom,
                u.prenom,
                u.email,
                u.date_creation,
                COUNT(DISTINCT c.id) as nombre_cours,
                COUNT(DISTINCT s.id) as nombre_seances_total
            FROM professeur p
            JOIN utilisateur u ON p.id = u.id
            LEFT JOIN cours c ON p.id = c.professeur_id
            LEFT JOIN seance s ON c.id = s.cours_id
            WHERE p.id = %s
            GROUP BY p.id, u.nom, u.prenom, u.email, u.date_creation
        """
        
        professeur = execute_query(query, (professeur_id,))
        
        if not professeur:
            logger.warning(f"Professeur non trouvé: ID {professeur_id}")
            return Error(code=404, message="Professeur non trouvé")
        
        return Success({
            "status": "success",
            "professeur": {
                "id": professeur["professeur_id"],
                "nom": professeur["nom"],
                "prenom": professeur["prenom"],
                "email": professeur["email"],
                "specialite": professeur["specialite"],
                "date_creation": professeur["date_creation"].isoformat() if professeur["date_creation"] else None,
                "statistiques": {
                    "nombre_cours": professeur["nombre_cours"],
                    "nombre_seances_total": professeur["nombre_seances_total"]
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_cours_professeur(professeur_id: int):
    """Récupère les cours d'un professeur"""
    logger.info(f"Récupération des cours pour le professeur ID: {professeur_id}")
    
    try:
        query = """
            SELECT 
                c.id,
                c.code,
                c.libelle,
                c.volume_horaire,
                COUNT(DISTINCT s.id) as nombre_seances,
                COUNT(DISTINCT g.id) as nombre_groupes
            FROM cours c
            LEFT JOIN seance s ON c.id = s.cours_id
            LEFT JOIN groupe g ON s.groupe_id = g.id
            WHERE c.professeur_id = %s
            GROUP BY c.id, c.code, c.libelle, c.volume_horaire
            ORDER BY c.libelle
        """
        
        cours = execute_query_all(query, (professeur_id,))
        
        result = []
        for c in cours:
            result.append({
                "id": c["id"],
                "code": c["code"],
                "libelle": c["libelle"],
                "volume_horaire": c["volume_horaire"],
                "statistiques": {
                    "nombre_seances": c["nombre_seances"],
                    "nombre_groupes": c["nombre_groupes"]
                }
            })
        
        logger.info(f"Nombre de cours trouvés: {len(result)}")
        
        return Success({
            "status": "success",
            "total": len(result),
            "cours": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des cours: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_seances_aujourdhui_professeur(professeur_id: int):
    """Récupère les séances d'aujourd'hui pour un professeur"""
    logger.info(f"Récupération des séances d'aujourd'hui pour le professeur ID: {professeur_id}")
    
    try:
        today = datetime.now().date()
        
        query = """
            SELECT 
                s.id,
                s.date,
                s.heure_debut,
                s.heure_fin,
                COALESCE(s.salle, 'Non spécifiée') as salle,
                c.libelle as cours_libelle,
                c.code as cours_code,
                g.nom as groupe_nom,
                COUNT(DISTINCT p.id) as nombre_etudiants,
                COUNT(DISTINCT CASE WHEN p.statut = 'PRESENT' THEN p.id END) as nombre_presents
            FROM seance s
            JOIN cours c ON s.cours_id = c.id
            JOIN groupe g ON s.groupe_id = g.id
            LEFT JOIN etudiant_groupe eg ON g.id = eg.groupe_id
            LEFT JOIN presence p ON s.id = p.seance_id AND eg.etudiant_id = p.etudiant_id
            WHERE c.professeur_id = %s 
            AND s.date = %s
            GROUP BY s.id, c.libelle, c.code, g.nom, s.date, s.heure_debut, s.heure_fin, s.salle
            ORDER BY s.heure_debut
        """
        
        seances = execute_query_all(query, (professeur_id, today))
        
        result = []
        for s in seances:
            taux_presence = round((s["nombre_presents"] / s["nombre_etudiants"] * 100), 2) if s["nombre_etudiants"] > 0 else 0
            
            result.append({
                "id": s["id"],
                "date": s["date"].isoformat(),
                "heure_debut": str(s["heure_debut"]),
                "heure_fin": str(s["heure_fin"]),
                "salle": s["salle"],
                "cours": {
                    "libelle": s["cours_libelle"],
                    "code": s["cours_code"]
                },
                "groupe": {
                    "nom": s["groupe_nom"]
                },
                "statistiques": {
                    "nombre_etudiants": s["nombre_etudiants"],
                    "nombre_presents": s["nombre_presents"],
                    "taux_presence": taux_presence
                }
            })
        
        logger.info(f"Nombre de séances aujourd'hui: {len(result)}")
        
        return Success({
            "status": "success",
            "date": today.isoformat(),
            "total": len(result),
            "seances": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des séances: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_seances_semaine_professeur(professeur_id: int):
    """Récupère les séances de la semaine pour un professeur"""
    logger.info(f"Récupération des séances de la semaine pour le professeur ID: {professeur_id}")
    
    try:
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        query = """
            SELECT 
                s.id,
                s.date,
                s.heure_debut,
                s.heure_fin,
                COALESCE(s.salle, 'Non spécifiée') as salle,
                c.libelle as cours_libelle,
                c.code as cours_code,
                g.nom as groupe_nom
            FROM seance s
            JOIN cours c ON s.cours_id = c.id
            JOIN groupe g ON s.groupe_id = g.id
            WHERE c.professeur_id = %s 
            AND s.date BETWEEN %s AND %s
            ORDER BY s.date, s.heure_debut
        """
        
        seances = execute_query_all(query, (professeur_id, start_of_week, end_of_week))
        
        result = []
        for s in seances:
            result.append({
                "id": s["id"],
                "date": s["date"].isoformat(),
                "heure_debut": str(s["heure_debut"]),
                "heure_fin": str(s["heure_fin"]),
                "salle": s["salle"],
                "cours": {
                    "libelle": s["cours_libelle"],
                    "code": s["cours_code"]
                },
                "groupe": {
                    "nom": s["groupe_nom"]
                }
            })
        
        logger.info(f"Nombre de séances cette semaine: {len(result)}")
        
        return Success({
            "status": "success",
            "start_of_week": start_of_week.isoformat(),
            "end_of_week": end_of_week.isoformat(),
            "total": len(result),
            "seances": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des séances de la semaine: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_statistiques_cours(professeur_id: int):
    """Récupère les statistiques des cours d'un professeur"""
    logger.info(f"Récupération des statistiques pour le professeur ID: {professeur_id}")
    
    try:
        query = """
            SELECT 
                c.id,
                c.libelle,
                COUNT(DISTINCT s.id) as nombre_seances,
                COUNT(DISTINCT g.id) as nombre_groupes,
                COUNT(DISTINCT p.id) as total_presences,
                SUM(CASE WHEN p.statut = 'PRESENT' THEN 1 ELSE 0 END) as presents,
                SUM(CASE WHEN p.statut = 'ABSENT_JUSTIFIE' THEN 1 ELSE 0 END) as absents_justifies,
                SUM(CASE WHEN p.statut = 'ABSENT_NON_JUSTIFIE' THEN 1 ELSE 0 END) as absents_non_justifies
            FROM cours c
            LEFT JOIN seance s ON c.id = s.cours_id
            LEFT JOIN groupe g ON s.groupe_id = g.id
            LEFT JOIN presence p ON s.id = p.seance_id
            WHERE c.professeur_id = %s
            GROUP BY c.id, c.libelle
            ORDER BY c.libelle
        """
        
        statistiques = execute_query_all(query, (professeur_id,))
        
        result = []
        total_stats = {
            "nombre_cours": 0,
            "nombre_seances": 0,
            "total_presences": 0,
            "presents": 0,
            "absents_justifies": 0,
            "absents_non_justifies": 0
        }
        
        for stat in statistiques:
            total = stat["total_presences"] or 0
            presents = stat["presents"] or 0
            taux_presence = round((presents / total * 100), 2) if total > 0 else 0
            
            result.append({
                "cours_id": stat["id"],
                "cours_libelle": stat["libelle"],
                "nombre_seances": stat["nombre_seances"],
                "nombre_groupes": stat["nombre_groupes"],
                "total_presences": total,
                "presents": presents,
                "absents_justifies": stat["absents_justifies"] or 0,
                "absents_non_justifies": stat["absents_non_justifies"] or 0,
                "taux_presence": taux_presence
            })
            
            # Aggréger les totaux
            total_stats["nombre_cours"] += 1
            total_stats["nombre_seances"] += (stat["nombre_seances"] or 0)
            total_stats["total_presences"] += total
            total_stats["presents"] += presents
            total_stats["absents_justifies"] += (stat["absents_justifies"] or 0)
            total_stats["absents_non_justifies"] += (stat["absents_non_justifies"] or 0)
        
        # Calculer le taux global
        total_taux = round((total_stats["presents"] / total_stats["total_presences"] * 100), 2) if total_stats["total_presences"] > 0 else 0
        
        logger.info(f"Statistiques récupérées pour {len(result)} cours")
        
        return Success({
            "status": "success",
            "statistiques_cours": result,
            "totaux": total_stats,
            "taux_presence_global": total_taux
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_absences_justifications_attente(professeur_id: int):
    """Récupère les justifications en attente pour les cours d'un professeur"""
    logger.info(f"Récupération des justifications en attente pour le professeur ID: {professeur_id}")
    
    try:
        query = """
            SELECT 
                p.id as presence_id,
                p.statut,
                p.justification,
                p.statut_justification,
                p.date_saisie,
                e.code_etudiant,
                CONCAT(u.nom, ' ', u.prenom) as nom_etudiant,
                s.date,
                s.heure_debut,
                s.heure_fin,
                c.libelle as cours_libelle,
                c.code as cours_code,
                g.nom as groupe_nom
            FROM presence p
            JOIN etudiant e ON p.etudiant_id = e.id
            JOIN utilisateur u ON e.id = u.id
            JOIN seance s ON p.seance_id = s.id
            JOIN cours c ON s.cours_id = c.id
            JOIN groupe g ON s.groupe_id = g.id
            WHERE c.professeur_id = %s
            AND p.statut = 'ABSENT_JUSTIFIE'
            AND p.statut_justification = 'EN_ATTENTE'
            ORDER BY s.date DESC, p.date_saisie DESC
        """
        
        justifications = execute_query_all(query, (professeur_id,))
        
        result = []
        for j in justifications:
            result.append({
                "presence_id": j["presence_id"],
                "etudiant": {
                    "code_etudiant": j["code_etudiant"],
                    "nom_complet": j["nom_etudiant"]
                },
                "justification": j["justification"],
                "date_saisie": j["date_saisie"].isoformat() if j["date_saisie"] else None,
                "seance": {
                    "date": j["date"].isoformat(),
                    "heure_debut": str(j["heure_debut"]),
                    "heure_fin": str(j["heure_fin"]),
                    "cours_libelle": j["cours_libelle"],
                    "cours_code": j["cours_code"],
                    "groupe_nom": j["groupe_nom"]
                }
            })
        
        logger.info(f"Nombre de justifications en attente: {len(result)}")
        
        return Success({
            "status": "success",
            "total": len(result),
            "justifications": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des justifications: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

# =========================================
# ENDPOINTS FLASK
# =========================================

@app.route("/", methods=["POST"])
def handle():
    """Point d'entrée pour toutes les requêtes RPC"""
    try:
        request_data = request.get_data().decode()
        logger.debug(f"Requête RPC professeur reçue: {request_data}")
        
        response = dispatch(request_data)
        
        logger.debug(f"Réponse RPC professeur: {response}")
        return response, 200, {"Content-Type": "application/json"}
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la requête RPC: {str(e)}")
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": 500,
                "message": f"Erreur interne du serveur: {str(e)}"
            },
            "id": None
        }), 500, {"Content-Type": "application/json"}

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de santé pour vérifier que le serveur fonctionne"""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        
        return json.dumps({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        }), 200, {"Content-Type": "application/json"}
        
    except Exception as e:
        return json.dumps({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected",
            "error": str(e)
        }), 500, {"Content-Type": "application/json"}

if __name__ == "__main__":
    logger.info("Démarrage du serveur RPC Flask pour professeurs...")
    
    try:
        conn = get_db_connection()
        logger.info("Connexion à la base de données établie avec succès")
        conn.close()
        
        app.run(host="127.0.0.1", port=5001, debug=True)
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du serveur: {str(e)}")
        raise