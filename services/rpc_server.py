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

# Connexion à PostgreSQL
def get_db_connection():
    """Établit une connexion à la base de données"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="gestion_absences",
            user="postgres",
            password="123456",
            port=5432
        )
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {str(e)}")
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
# FONCTIONS RPC PRINCIPALES
# =========================================

@method
def login_etudiant(email: str, mot_de_passe: str):
    """Connexion étudiant - Fonction principale"""
    logger.info(f"Tentative de connexion pour l'email: {email}")
    
    if not email or not mot_de_passe:
        return Error(code=400, message="Email et mot de passe requis")
    
    try:
        user = execute_query(
            "SELECT e.id as etudiant_id, e.code_etudiant, u.nom, u.prenom, u.mot_de_passe "
            "FROM etudiant e JOIN utilisateur u ON e.id = u.id WHERE u.email = %s",
            (email,)
        )

        if not user:
            logger.warning(f"Email non trouvé: {email}")
            return Error(code=401, message="Email incorrect")
        
        if user["mot_de_passe"] != mot_de_passe:
            logger.warning(f"Mot de passe incorrect pour l'email: {email}")
            return Error(code=401, message="Mot de passe incorrect")

        logger.info(f"Connexion réussie pour l'étudiant ID: {user['etudiant_id']}")
        return Success({
            "status": "success",
            "etudiant_id": user["etudiant_id"],
            "code_etudiant": user["code_etudiant"],
            "nom": user["nom"],
            "prenom": user["prenom"]
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_info_etudiant(etudiant_id: int):
    """Récupère les informations complètes d'un étudiant"""
    logger.info(f"Récupération des informations pour l'étudiant ID: {etudiant_id}")
    
    try:
        query = """
            SELECT 
                e.id as etudiant_id,
                e.code_etudiant,
                e.promotion_id,
                u.nom,
                u.prenom,
                u.email,
                u.date_creation,
                p.libelle as promotion_libelle,
                p.annee_scolaire,
                f.nom as filiere_nom,
                f.code as filiere_code,
                f.niveau as filiere_niveau
            FROM etudiant e
            JOIN utilisateur u ON e.id = u.id
            LEFT JOIN promotion p ON e.promotion_id = p.id
            LEFT JOIN filiere f ON p.filiere_id = f.id
            WHERE e.id = %s
        """
        
        etudiant = execute_query(query, (etudiant_id,))
        
        if not etudiant:
            logger.warning(f"Étudiant non trouvé: ID {etudiant_id}")
            return Error(code=404, message="Étudiant non trouvé")
        
        return Success({
            "status": "success",
            "etudiant": {
                "id": etudiant["etudiant_id"],
                "code_etudiant": etudiant["code_etudiant"],
                "nom": etudiant["nom"],
                "prenom": etudiant["prenom"],
                "email": etudiant["email"],
                "date_creation": etudiant["date_creation"].isoformat() if etudiant["date_creation"] else None,
                "promotion": {
                    "id": etudiant["promotion_id"],
                    "libelle": etudiant["promotion_libelle"],
                    "annee_scolaire": etudiant["annee_scolaire"]
                } if etudiant["promotion_id"] else None,
                "filiere": {
                    "nom": etudiant["filiere_nom"],
                    "code": etudiant["filiere_code"],
                    "niveau": etudiant["filiere_niveau"]
                } if etudiant["filiere_nom"] else None
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_groupes_etudiant(etudiant_id: int):
    """Récupère les groupes d'un étudiant"""
    logger.info(f"Récupération des groupes pour l'étudiant ID: {etudiant_id}")
    
    try:
        query = """
            SELECT 
                g.id,
                g.nom,
                p.libelle as promotion_libelle,
                p.annee_scolaire
            FROM groupe g
            JOIN promotion p ON g.promotion_id = p.id
            JOIN etudiant_groupe eg ON g.id = eg.groupe_id
            WHERE eg.etudiant_id = %s
            ORDER BY g.nom
        """
        
        groupes = execute_query_all(query, (etudiant_id,))
        
        result = []
        for g in groupes:
            result.append({
                "id": g["id"],
                "nom": g["nom"],
                "promotion": {
                    "libelle": g["promotion_libelle"],
                    "annee_scolaire": g["annee_scolaire"]
                }
            })
        
        logger.info(f"Nombre de groupes trouvés: {len(result)}")
        
        return Success({
            "status": "success",
            "total": len(result),
            "groupes": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des groupes: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_seances_aujourdhui(etudiant_id: int):
    """Récupère les séances d'aujourd'hui pour un étudiant"""
    logger.info(f"Récupération des séances d'aujourd'hui pour l'étudiant ID: {etudiant_id}")
    
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
                g.nom as groupe_nom
            FROM seance s
            JOIN cours c ON s.cours_id = c.id
            JOIN groupe g ON s.groupe_id = g.id
            JOIN etudiant_groupe eg ON g.id = eg.groupe_id
            WHERE eg.etudiant_id = %s 
            AND s.date = %s
            ORDER BY s.heure_debut
        """
        
        seances = execute_query_all(query, (etudiant_id, today))
        
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
def get_seances_semaine(etudiant_id: int):
    """Récupère les séances de la semaine pour un étudiant"""
    logger.info(f"Récupération des séances de la semaine pour l'étudiant ID: {etudiant_id}")
    
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
            JOIN etudiant_groupe eg ON g.id = eg.groupe_id
            WHERE eg.etudiant_id = %s 
            AND s.date BETWEEN %s AND %s
            ORDER BY s.date, s.heure_debut
        """
        
        seances = execute_query_all(query, (etudiant_id, start_of_week, end_of_week))
        
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
def get_absences_etudiant(etudiant_id: int):
    """Récupère les absences d'un étudiant"""
    logger.info(f"Récupération des absences pour l'étudiant ID: {etudiant_id}")
    
    try:
        query = """
            SELECT 
                p.id,
                p.statut,
                COALESCE(p.justification, '') as justification,
                COALESCE(p.statut_justification, 'EN_ATTENTE') as statut_justification,
                p.date_saisie,
                s.date,
                s.heure_debut,
                s.heure_fin,
                COALESCE(s.salle, 'Non spécifiée') as salle,
                c.libelle as cours_libelle,
                c.code as cours_code,
                g.nom as groupe_nom
            FROM presence p
            JOIN seance s ON p.seance_id = s.id
            JOIN cours c ON s.cours_id = c.id
            JOIN groupe g ON s.groupe_id = g.id
            WHERE p.etudiant_id = %s
            AND p.statut IN ('ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE')
            ORDER BY s.date DESC
        """
        
        absences = execute_query_all(query, (etudiant_id,))
        
        result = []
        for a in absences:
            result.append({
                "id": a["id"],
                "statut": a["statut"],
                "justification": a["justification"],
                "statut_justification": a["statut_justification"],
                "date_saisie": a["date_saisie"].isoformat() if a["date_saisie"] else None,
                "seance": {
                    "date": a["date"].isoformat(),
                    "heure_debut": str(a["heure_debut"]),
                    "heure_fin": str(a["heure_fin"]),
                    "salle": a["salle"]
                },
                "cours": {
                    "libelle": a["cours_libelle"],
                    "code": a["cours_code"]
                },
                "groupe": {
                    "nom": a["groupe_nom"]
                }
            })
        
        # Calculer les statistiques
        total_absences = len(result)
        absences_justifiees = len([a for a in result if a["statut"] == "ABSENT_JUSTIFIE"])
        absences_non_justifiees = total_absences - absences_justifiees
        
        logger.info(f"Nombre d'absences trouvées: {total_absences}")
        
        return Success({
            "status": "success",
            "total": total_absences,
            "absences_justifiees": absences_justifiees,
            "absences_non_justifiees": absences_non_justifiees,
            "absences": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des absences: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_notifications_etudiant(etudiant_id: int, non_lues_seulement: bool = False):
    """Récupère les notifications d'un étudiant"""
    logger.info(f"Récupération des notifications pour l'étudiant ID: {etudiant_id}")
    
    try:
        query = """
            SELECT 
                n.id,
                n.message,
                n.date_envoi,
                n.lu,
                COALESCE(p.statut, '') as presence_statut,
                COALESCE(c.libelle, '') as cours_libelle
            FROM notification n
            LEFT JOIN presence p ON n.presence_id = p.id
            LEFT JOIN seance s ON p.seance_id = s.id
            LEFT JOIN cours c ON s.cours_id = c.id
            WHERE n.etudiant_id = %s
        """
        
        params = [etudiant_id]
        
        if non_lues_seulement:
            query += " AND n.lu = FALSE"
        
        query += " ORDER BY n.date_envoi DESC"
        
        notifications = execute_query_all(query, tuple(params))
        
        result = []
        for n in notifications:
            result.append({
                "id": n["id"],
                "message": n["message"],
                "date_envoi": n["date_envoi"].isoformat() if n["date_envoi"] else None,
                "lu": n["lu"],
                "presence": {
                    "statut": n["presence_statut"],
                    "cours_libelle": n["cours_libelle"]
                } if n["presence_statut"] else None
            })
        
        # Compter les notifications non lues
        count_query = "SELECT COUNT(*) as count FROM notification WHERE etudiant_id = %s AND lu = FALSE"
        count_result = execute_query(count_query, (etudiant_id,))
        non_lues_count = count_result["count"] if count_result else 0
        
        logger.info(f"Notifications trouvées: {len(result)}, non lues: {non_lues_count}")
        
        return Success({
            "status": "success",
            "total": len(result),
            "non_lues_count": non_lues_count,
            "notifications": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des notifications: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def marquer_notifications_lues(etudiant_id: int):
    """Marque toutes les notifications comme lues"""
    logger.info(f"Marquage des notifications comme lues pour l'étudiant ID: {etudiant_id}")
    
    try:
        rows_updated = execute_update(
            "UPDATE notification SET lu = TRUE WHERE etudiant_id = %s AND lu = FALSE",
            (etudiant_id,)
        )
        
        logger.info(f"{rows_updated} notification(s) marquée(s) comme lue(s)")
        
        return Success({
            "status": "success",
            "message": f"{rows_updated} notification(s) marquée(s) comme lue(s)"
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du marquage des notifications: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_statistiques_presence(etudiant_id: int):
    """Récupère les statistiques de présence d'un étudiant"""
    logger.info(f"Récupération des statistiques pour l'étudiant ID: {etudiant_id}")
    
    try:
        query = """
            SELECT 
                COUNT(*) as total_seances,
                SUM(CASE WHEN p.statut = 'PRESENT' THEN 1 ELSE 0 END) as presents,
                SUM(CASE WHEN p.statut = 'ABSENT_JUSTIFIE' THEN 1 ELSE 0 END) as absents_justifies,
                SUM(CASE WHEN p.statut = 'ABSENT_NON_JUSTIFIE' THEN 1 ELSE 0 END) as absents_non_justifies
            FROM presence p
            WHERE p.etudiant_id = %s
        """
        
        stats = execute_query(query, (etudiant_id,))
        
        if not stats:
            return Success({
                "status": "success",
                "total_seances": 0,
                "presents": 0,
                "absents_justifies": 0,
                "absents_non_justifies": 0,
                "taux_presence": 0
            })
        
        total = stats["total_seances"] or 0
        presents = stats["presents"] or 0
        taux = round((presents / total * 100), 2) if total > 0 else 0
        
        logger.info(f"Statistiques: total={total}, présents={presents}, taux={taux}%")
        
        return Success({
            "status": "success",
            "total_seances": total,
            "presents": presents,
            "absents_justifies": stats["absents_justifies"] or 0,
            "absents_non_justifies": stats["absents_non_justifies"] or 0,
            "taux_presence": taux,
            "total_absences": (stats["absents_justifies"] or 0) + (stats["absents_non_justifies"] or 0)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def get_presences_etudiant(etudiant_id: int, statut: str = None):
    """Récupère toutes les présences d'un étudiant avec filtre optionnel"""
    logger.info(f"Récupération des présences pour l'étudiant ID: {etudiant_id}, filtre: {statut}")
    
    try:
        query = """
            SELECT 
                p.id,
                p.statut,
                COALESCE(p.justification, '') as justification,
                COALESCE(p.statut_justification, 'EN_ATTENTE') as statut_justification,
                COALESCE(p.feedback_professeur, '') as feedback_professeur,
                p.date_saisie,
                s.date,
                s.heure_debut,
                s.heure_fin,
                COALESCE(s.salle, 'Non spécifiée') as salle,
                c.libelle as cours_libelle,
                c.code as cours_code,
                g.nom as groupe_nom
            FROM presence p
            JOIN seance s ON p.seance_id = s.id
            JOIN cours c ON s.cours_id = c.id
            JOIN groupe g ON s.groupe_id = g.id
            WHERE p.etudiant_id = %s
        """
        
        params = [etudiant_id]
        
        if statut and statut != "TOUS":
            query += " AND p.statut = %s"
            params.append(statut)
        
        query += " ORDER BY s.date DESC, s.heure_debut DESC"
        
        presences = execute_query_all(query, tuple(params))
        
        result = []
        for p in presences:
            result.append({
                "id": p["id"],
                "statut": p["statut"],
                "justification": p["justification"],
                "statut_justification": p["statut_justification"],
                "feedback_professeur": p["feedback_professeur"],
                "date_saisie": p["date_saisie"].isoformat() if p["date_saisie"] else None,
                "seance": {
                    "date": p["date"].isoformat(),
                    "heure_debut": str(p["heure_debut"]),
                    "heure_fin": str(p["heure_fin"]),
                    "salle": p["salle"]
                },
                "cours": {
                    "libelle": p["cours_libelle"],
                    "code": p["cours_code"]
                },
                "groupe": {
                    "nom": p["groupe_nom"]
                }
            })
        
        # Calculer les statistiques
        total = len(result)
        presents = len([p for p in result if p["statut"] == "PRESENT"])
        abs_justifies = len([p for p in result if p["statut"] == "ABSENT_JUSTIFIE"])
        abs_non_justifies = len([p for p in result if p["statut"] == "ABSENT_NON_JUSTIFIE"])
        
        logger.info(f"Nombre de présences trouvées: {total}")
        
        return Success({
            "status": "success",
            "total": total,
            "presents": presents,
            "absents_justifies": abs_justifies,
            "absents_non_justifies": abs_non_justifies,
            "presences": result
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des présences: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

@method
def ajouter_justification_absence(etudiant_id: int, presence_id: int, justification: str):
    """Ajoute une justification à une absence"""
    logger.info(f"Ajout de justification pour la présence ID: {presence_id}")
    
    try:
        # Vérifier que la présence appartient à l'étudiant
        check_query = """
            SELECT id, statut, justification
            FROM presence 
            WHERE id = %s AND etudiant_id = %s
        """
        presence = execute_query(check_query, (presence_id, etudiant_id))
        
        if not presence:
            logger.warning(f"Présence non trouvée: ID {presence_id}")
            return Error(code=404, message="Présence non trouvée")
        
        if presence["statut"] != "ABSENT_NON_JUSTIFIE":
            logger.warning(f"La présence n'est pas une absence non justifiée")
            return Error(code=400, message="Cette absence ne peut pas être justifiée")
        
        if presence["justification"]:
            logger.warning(f"La présence a déjà une justification")
            return Error(code=400, message="Cette absence a déjà une justification")
        
        # Mettre à jour la présence
        update_query = """
            UPDATE presence 
            SET justification = %s, 
                statut_justification = 'EN_ATTENTE',
                date_saisie = NOW()
            WHERE id = %s AND etudiant_id = %s
        """
        
        rows_updated = execute_update(update_query, (justification, presence_id, etudiant_id))
        
        if rows_updated == 0:
            logger.error(f"Aucune ligne mise à jour")
            return Error(code=500, message="Erreur lors de la mise à jour")
        
        logger.info(f"Justification ajoutée avec succès")
        
        return Success({
            "status": "success",
            "message": "Justification ajoutée avec succès. Elle sera examinée par le professeur."
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de justification: {str(e)}")
        return Error(code=500, message=f"Erreur serveur: {str(e)}")

# =========================================
# ENDPOINTS FLASK
# =========================================

@app.route("/", methods=["POST"])
def handle():
    """Point d'entrée pour toutes les requêtes RPC"""
    try:
        request_data = request.get_data().decode()
        logger.debug(f"Requête RPC reçue: {request_data}")
        
        response = dispatch(request_data)
        
        logger.debug(f"Réponse RPC: {response}")
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
        # Tester la connexion à la base de données
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
    logger.info("Démarrage du serveur RPC Flask...")
    
    try:
        # Tester la connexion à la base de données au démarrage
        conn = get_db_connection()
        logger.info("Connexion à la base de données établie avec succès")
        conn.close()
        
        app.run(host="127.0.0.1", port=5000, debug=True)
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du serveur: {str(e)}")
        raise