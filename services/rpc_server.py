<<<<<<< HEAD
import json
from datetime import date as dt_date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from services.stats_rpc import dashboard_stats
from services.db import get_conn
from services import auth
from services.auth import hash_password, verify_password
import uuid

TOKENS = {
    "rpc": "mon_super_token_12345"
}

def ok(rpc_id, result):
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

def err(rpc_id, code, message):
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}

def q_one(cur):
    row = cur.fetchone()
    return row[0] if row else None

def stats_dashboard():
    return dashboard_stats()

# -----------------------------
# COURSES
# -----------------------------

def course_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            c.id,
            c.code,
            c.libelle,
            c.volume_horaire,
            c.professeur_id,
            COALESCE(u.nom, ''),
            COALESCE(u.prenom, '')
        FROM cours c
        LEFT JOIN professeur p ON p.id = c.professeur_id
        LEFT JOIN utilisateur u ON u.id = p.id
        ORDER BY c.id
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    result = []
    for r in rows:
        nom = (r[5] or "").strip()
        prenom = (r[6] or "").strip()
        full = (f"{nom} {prenom}").strip() if (nom or prenom) else None

        result.append({
            "id": r[0],
            "code": r[1],
            "libelle": r[2],
            "volumeHoraire": r[3],
            "professorId": r[4],
            "profFullName": full,
        })
    return result

def course_create(p):
    code = (p.get("code") or "").strip()
    libelle = (p.get("libelle") or "").strip()
    volume = p.get("volumeHoraire", None)

    if not code or not libelle or volume is None:
        raise ValueError("course.create: code, libelle, volumeHoraire requis")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cours(code, libelle, volume_horaire) VALUES (%s, %s, %s) RETURNING id",
        (code, libelle, int(volume))
    )
    new_id = q_one(cur)
    conn.commit()
    cur.close(); conn.close()
    return {"id": new_id, "code": code, "libelle": libelle, "volumeHoraire": int(volume), "professorId": None}

def course_update(p):
    course_id = p.get("id")
    if not course_id:
        raise ValueError("course.update: id requis")

    fields = []
    values = []

    if "code" in p:
        fields.append("code=%s"); values.append(p["code"])
    if "libelle" in p:
        fields.append("libelle=%s"); values.append(p["libelle"])
    if "volumeHoraire" in p:
        fields.append("volume_horaire=%s"); values.append(int(p["volumeHoraire"]))
    if "professorId" in p:
        prof_id = p.get("professorId")
        if prof_id in ("", "null"):
            prof_id = None
        elif prof_id is not None:
            prof_id = int(prof_id)
        fields.append("professeur_id=%s")
        values.append(prof_id)

    if not fields:
        raise ValueError("course.update: aucun champ à mettre à jour")

    values.append(int(course_id))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE cours SET {', '.join(fields)} WHERE id=%s", tuple(values))
    if cur.rowcount == 0:
        conn.rollback()
        cur.close(); conn.close()
        raise ValueError("Cours introuvable")
    conn.commit()
    cur.close(); conn.close()
    return True

def course_delete(p):
    course_id = p.get("id")
    if not course_id:
        raise ValueError("course.delete: id requis")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM cours WHERE id=%s", (course_id,))
    if cur.rowcount == 0:
        conn.rollback()
        cur.close(); conn.close()
        raise ValueError("Cours introuvable")
    conn.commit()
    cur.close(); conn.close()
    return True

# -----------------------------
# STUDENTS
# -----------------------------

def student_list(p):
    promo = None
    if p:
        promo = p.get("promotionId")

    conn = get_conn()
    cur = conn.cursor()

    if promo is None:
        cur.execute("""
            SELECT e.id, u.nom, u.prenom, u.email, e.promotion_id, e.code_etudiant
            FROM etudiant e
            JOIN utilisateur u ON u.id = e.id
            ORDER BY e.id
        """)
    else:
        cur.execute("""
            SELECT e.id, u.nom, u.prenom, u.email, e.promotion_id, e.code_etudiant
            FROM etudiant e
            JOIN utilisateur u ON u.id = e.id
            WHERE e.promotion_id = %s
            ORDER BY e.id
        """, (int(promo),))

    rows = cur.fetchall()
    cur.close(); conn.close()

    return [
        {
            "id": r[0],
            "nom": r[1],
            "prenom": r[2],
            "email": r[3],
            "promotionId": r[4],
            "codeEtudiant": r[5],
        }
        for r in rows
    ]

def student_create(p):
    nom = (p.get("nom") or "").strip()
    prenom = (p.get("prenom") or "").strip()
    email = (p.get("email") or "").strip()
    promotion_id = p.get("promotionId")
    code_et = (p.get("codeEtudiant") or "").strip()
    mot_de_passe = (p.get("motDePasse") or "").strip()

    if not nom or not prenom or not email or promotion_id is None:
        raise ValueError("student.create: nom, prenom, email, promotionId requis")
    if not mot_de_passe:
        raise ValueError("student.create: motDePasse requis")

    promotion_id = int(promotion_id)

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM promotion WHERE id=%s", (promotion_id,))
        if cur.fetchone() is None:
            raise ValueError("Promotion invalide")

        cur.execute(
            """
            INSERT INTO utilisateur (nom, prenom, email, mot_de_passe, type_utilisateur)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (nom, prenom, email, mot_de_passe, "ETUDIANT")
        )
        user_id = q_one(cur)

        cur.execute(
            """
            INSERT INTO etudiant (id, promotion_id, code_etudiant)
            VALUES (%s, %s, %s)
            """,
            (int(user_id), promotion_id, code_et or None)
        )

        conn.commit()
        return {
            "id": int(user_id),
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "promotionId": promotion_id,
            "codeEtudiant": code_et or None
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def student_update(p):
    student_id = p.get("id")
    if not student_id:
        raise ValueError("student.update: id requis")

    nom = p.get("nom")
    prenom = p.get("prenom")
    email = p.get("email")
    mot_de_passe = p.get("motDePasse") if "motDePasse" in p else p.get("mot_de_passe")
    promotion_id = p.get("promotionId")
    code_et = p.get("codeEtudiant")

    if all(v is None for v in [nom, prenom, email, mot_de_passe, promotion_id, code_et]):
        raise ValueError("student.update: aucun champ à mettre à jour")

    conn = get_conn()
    cur = conn.cursor()

    u_fields = []
    u_vals = []
    if nom is not None:
        u_fields.append("nom=%s"); u_vals.append(nom)
    if prenom is not None:
        u_fields.append("prenom=%s"); u_vals.append(prenom)
    if email is not None:
        u_fields.append("email=%s"); u_vals.append(email)
    if mot_de_passe is not None:
        u_fields.append("mot_de_passe=%s"); u_vals.append(mot_de_passe)

    if u_fields:
        u_vals.append(int(student_id))
        cur.execute(f"UPDATE utilisateur SET {', '.join(u_fields)} WHERE id=%s", tuple(u_vals))
        if cur.rowcount == 0:
            conn.rollback()
            cur.close(); conn.close()
            raise ValueError("Utilisateur introuvable")

    e_fields = []
    e_vals = []
    if promotion_id is not None:
        e_fields.append("promotion_id=%s"); e_vals.append(int(promotion_id))
    if code_et is not None:
        e_fields.append("code_etudiant=%s"); e_vals.append(code_et)

    if e_fields:
        e_vals.append(int(student_id))
        cur.execute(f"UPDATE etudiant SET {', '.join(e_fields)} WHERE id=%s", tuple(e_vals))
        if cur.rowcount == 0:
            conn.rollback()
            cur.close(); conn.close()
            raise ValueError("Etudiant introuvable")

    conn.commit()
    cur.close(); conn.close()
    return True

def student_delete(p):
    student_id = p.get("id")
    if not student_id:
        raise ValueError("student.delete: id requis")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM utilisateur WHERE id=%s", (int(student_id),))
    if cur.rowcount == 0:
        conn.rollback()
        cur.close(); conn.close()
        raise ValueError("Etudiant/Utilisateur introuvable")

    conn.commit()
    cur.close(); conn.close()
    return True

# -----------------------------
# ABSENCES (FONCTION CORRIGÉE)
# -----------------------------
def student_absences_over_limit(params):
    """Récupérer les étudiants avec plus de X absences - VERSION SIMPLIFIÉE"""
    limit = int(params.get("limit", 0))
    filiere_id = params.get("filiereId")
    
    print(f"\n[RPC] Filtres: limit={limit}, filiere={filiere_id}")
    
    conn = get_conn()
    cur = conn.cursor()
    
    query = """
        SELECT 
            e.id,
            u.nom,
            u.prenom,
            u.email,
            pr.libelle as promotion,
            f.nom as filiere,
            c.code as cours_code,
            c.libelle as cours_libelle,
            COUNT(p.id) as nombre_absences,
            STRING_AGG(DISTINCT TO_CHAR(s.date, 'DD/MM/YYYY'), ', ') as dates_absences
        FROM presence p
        JOIN etudiant e ON e.id = p.etudiant_id
        JOIN utilisateur u ON u.id = e.id
        JOIN seance s ON s.id = p.seance_id
        JOIN cours c ON c.id = s.cours_id
        JOIN promotion pr ON pr.id = e.promotion_id
        JOIN filiere f ON f.id = pr.filiere_id
        WHERE p.statut = 'ABSENT_NON_JUSTIFIE'
    """
    
    params_list = []
    
    if filiere_id:
        query += " AND f.id = %s"
        params_list.append(int(filiere_id))
    
    query += """
        GROUP BY e.id, u.nom, u.prenom, u.email, pr.libelle, f.nom, c.code, c.libelle
    """
    
    if limit > 0:
        query += " HAVING COUNT(p.id) >= %s"
        params_list.append(limit)
    
    query += " ORDER BY nombre_absences DESC, u.nom, u.prenom"
    
    cur.execute(query, tuple(params_list))
    rows = cur.fetchall()
    
    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "nom": r[1],
            "prenom": r[2],
            "email": r[3],
            "promotion": r[4],
            "filiere": r[5],
            "cours_code": r[6],
            "cours_libelle": r[7],
            "nombre_absences": r[8],
            "dates_absences": r[9] if r[9] else "-"
        })
    
    cur.close()
    conn.close()
    
    print(f"[RPC] {len(result)} résultats retournés")
    return result
# -----------------------------
# PLANNING / SEANCE
# -----------------------------

def planning_get_day(p):
    d = p.get("date")
    if not d:
        raise ValueError("planning.getDay: date (YYYY-MM-DD) requis")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, heure_debut, heure_fin, salle, cours_id, groupe_id, planning_id
        FROM seance
        WHERE date = %s
        ORDER BY heure_debut
    """, (d,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "date": str(r[1]), "heureDebut": str(r[2]), "heureFin": str(r[3]), "salle": r[4],
         "courseId": r[5], "groupeId": r[6], "planningId": r[7]}
        for r in rows
    ]

def planning_get_week(p):
    week = int(p.get("week"))
    year = int(p.get("year"))
    
    monday = dt_date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, semaine, annee FROM planning 
        WHERE semaine = %s AND annee = %s
        LIMIT 1
    """, (week, year))
    
    planning_row = cur.fetchone()
    
    if not planning_row:
        cur.close()
        conn.close()
        return []
    
    planning_id = planning_row[0]
    
    cur.execute("""
    SELECT 
        s.id, s.date, s.heure_debut, s.heure_fin, s.salle,
        c.code, c.libelle,
        g.nom AS groupe
    FROM seance s
    JOIN cours c ON s.cours_id = c.id
    JOIN groupe g ON s.groupe_id = g.id
    WHERE s.planning_id = %s 
      AND s.date BETWEEN %s AND %s
    ORDER BY s.date, s.heure_debut
    """, (planning_id, monday, sunday))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return [
        {
            "id": r[0],
            "date": str(r[1]),
            "heureDebut": str(r[2]),
            "heureFin": str(r[3]),
            "salle": r[4],
            "cours": f"{r[5]} - {r[6]}" if r[5] else "Sans cours",
            "groupe": r[7] if r[7] else "Sans groupe",
        }
        for r in rows
    ]

def seance_get(params):
    """Récupérer une séance par son ID"""
    seance_id = int(params.get("id"))
    
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            s.id, s.date, s.heure_debut, s.heure_fin, s.salle,
            s.cours_id, c.code, c.libelle,
            s.groupe_id, g.nom,
            s.planning_id
        FROM seance s
        LEFT JOIN cours c ON c.id = s.cours_id
        LEFT JOIN groupe g ON g.id = s.groupe_id
        WHERE s.id = %s
    """, (seance_id,))
    
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "date": str(row[1]),
        "heureDebut": str(row[2]),
        "heureFin": str(row[3]),
        "salle": row[4],
        "cours_id": row[5],
        "cours": f"{row[6]} - {row[7]}" if row[6] else "",
        "groupe_id": row[8],
        "groupe": row[9] if row[9] else "",
        "planning_id": row[10]
    }

def seance_add(p):
    conn = get_conn()
    cur = conn.cursor()

    date = p.get("date")
    hd = p.get("heure_debut")
    hf = p.get("heure_fin")
    salle = p.get("salle")
    cours_id = int(p.get("cours"))
    groupe_id = int(p.get("groupe"))
    planning_id = int(p.get("planning_id"))

    date_obj = dt_date.fromisoformat(date)
    date_semaine = date_obj.isocalendar()[1]
    date_annee = date_obj.isocalendar()[0]
    
    cur.execute("SELECT semaine, annee FROM planning WHERE id = %s", (planning_id,))
    planning_info = cur.fetchone()
    
    if planning_info:
        planning_semaine = planning_info[0]
        planning_annee = planning_info[1]
        
        if date_semaine != planning_semaine or date_annee != planning_annee:
            cur.close()
            conn.close()
            raise ValueError(
                f"La date {date} (semaine {date_semaine}) ne correspond pas "
                f"au planning {planning_id} (semaine {planning_semaine})"
            )

    cur.execute("""
        SELECT COUNT(*) FROM seance
        WHERE date=%s AND (
            (heure_debut < %s AND heure_fin > %s) 
            OR (heure_debut < %s AND heure_fin > %s)
        )
        AND salle=%s
    """, (date, hf, hd, hf, hd, salle))

    if cur.fetchone()[0] > 0:
        cur.close()
        conn.close()
        raise ValueError(f"Salle {salle} déjà occupée à cet horaire")

    cur.execute("""
        INSERT INTO seance(date, heure_debut, heure_fin, salle, cours_id, groupe_id, planning_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (date, hd, hf, salle, cours_id, groupe_id, planning_id))

    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        "status": "success",
        "id": new_id
    }

def seance_update(params):
    """Mettre à jour une séance"""
    seance_id = int(params.get("id"))
    date = params.get("date")
    heure_debut = params.get("heure_debut")
    heure_fin = params.get("heure_fin")
    salle = params.get("salle")
    cours_id = params.get("cours")
    groupe_id = params.get("groupe")
    
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM seance WHERE id = %s", (seance_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise ValueError(f"Séance {seance_id} non trouvée")
    
    update_fields = []
    update_values = []
    
    if date:
        update_fields.append("date = %s")
        update_values.append(date)
    
    if heure_debut:
        update_fields.append("heure_debut = %s")
        update_values.append(heure_debut)
    
    if heure_fin:
        update_fields.append("heure_fin = %s")
        update_values.append(heure_fin)
    
    if salle:
        update_fields.append("salle = %s")
        update_values.append(salle)
    
    if cours_id:
        update_fields.append("cours_id = %s")
        update_values.append(int(cours_id))
    
    if groupe_id:
        update_fields.append("groupe_id = %s")
        update_values.append(int(groupe_id))
    
    if not update_fields:
        cur.close()
        conn.close()
        raise ValueError("Aucun champ à mettre à jour")
    
    update_values.append(seance_id)
    
    query = f"UPDATE seance SET {', '.join(update_fields)} WHERE id = %s"
    cur.execute(query, tuple(update_values))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"status": "success", "id": seance_id}

def seance_delete(params):
    """Supprimer une séance"""
    seance_id = int(params.get("id"))
    
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM seance WHERE id = %s", (seance_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise ValueError(f"Séance {seance_id} non trouvée")
    
    cur.execute("DELETE FROM seance WHERE id = %s", (seance_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"status": "success", "id": seance_id}

def planning_generate(p):
    week = int(p.get("week"))
    year = int(p.get("year"))
    admin_id = int(p.get("administrateurId", 1))
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id FROM planning 
            WHERE semaine = %s AND annee = %s
            LIMIT 1
        """, (week, year))
        
        existing = cur.fetchone()
        
        if existing:
            planning_id = existing[0]
            return {
                "planningId": planning_id, 
                "message": f"Planning semaine {week} - {year} existe déjà (ID: {planning_id})",
                "alreadyExists": True
            }
        
        cur.execute("""
            INSERT INTO planning(semaine, annee, administrateur_id, date_creation)
            VALUES (%s, %s, %s, NOW()) 
            RETURNING id
        """, (week, year, admin_id))
        
        planning_id = cur.fetchone()[0]
        
        cur.execute("SELECT id FROM cours WHERE id = 1")
        course_id = cur.fetchone()
        
        cur.execute("SELECT id FROM groupe WHERE id = 1")  
        groupe_id = cur.fetchone()
        
        if not course_id or not groupe_id:
            conn.rollback()
            raise ValueError("Il faut au moins 1 cours et 1 groupe dans la base")
        
        course_id = course_id[0]
        groupe_id = groupe_id[0]
        
        monday = dt_date.fromisocalendar(year, week, 1)
        seances = [
            (str(monday), "08:00:00", "10:00:00", "A1"),
            (str(monday + timedelta(days=2)), "10:00:00", "12:00:00", "B2"),
            (str(monday + timedelta(days=4)), "14:00:00", "16:00:00", "C3"),
        ]
        
        for date, hd, hf, salle in seances:
            cur.execute("""
                INSERT INTO seance(date, heure_debut, heure_fin, salle, 
                                  cours_id, groupe_id, planning_id)
                VALUES(%s, %s, %s, %s, %s, %s, %s)
            """, (date, hd, hf, salle, course_id, groupe_id, planning_id))
        
        conn.commit()
        
        return {
            "planningId": planning_id, 
            "createdSeances": len(seances),
            "message": f"Planning semaine {week} - {year} créé avec succès"
        }
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

# -----------------------------
# UTILITAIRES
# -----------------------------

def cours_get_all(params=None):
    """Récupérer tous les cours"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, code, libelle, volume_horaire 
        FROM cours 
        ORDER BY code
    """)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return [
        {
            "id": r[0],
            "code": r[1],
            "libelle": r[2],
            "volumeHoraire": r[3]
        }
        for r in rows
    ]

def groupe_get_all(params=None):
    """Récupérer tous les groupes"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, nom, promotion_id 
        FROM groupe 
        ORDER BY nom
    """)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return [
        {
            "id": r[0],
            "nom": r[1],
            "promotionId": r[2]
        }
        for r in rows
    ]

def professor_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, u.nom, u.prenom
        FROM professeur p
        JOIN utilisateur u ON u.id = p.id
        ORDER BY u.nom
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    return [
        {
            "id": r[0],
            "nom": r[1],
            "prenom": r[2],
            "fullName": f"{r[1]} {r[2]}"
        } for r in rows
    ]

def filiere_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, nom FROM filiere ORDER BY nom")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"id": r[0], "nom": r[1]} for r in rows]

def promotion_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, libelle FROM promotion ORDER BY libelle")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"id": r[0], "libelle": r[1]} for r in rows]

def user_get(params):
    """Récupérer un utilisateur par son ID"""
    try:
        user_id_str = params.get("id")
        if not user_id_str:
            return None
        
        user_id = int(user_id_str)
        
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, nom, prenom, email, type_utilisateur, date_creation
            FROM utilisateur 
            WHERE id = %s
        """, (user_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "nom": row[1],
            "prenom": row[2],
            "email": row[3],
            "type_utilisateur": row[4],
            "date_creation": str(row[5]) if row[5] else None
        }
        
    except ValueError as e:
        return None
    except Exception as e:
        return None

def user_update(params):
    """Mettre à jour un utilisateur"""
    user_id = int(params.get("id"))
    nom = params.get("nom")
    prenom = params.get("prenom")
    email = params.get("email")
    mot_de_passe = params.get("motDePasse")
    
    conn = get_conn()
    cur = conn.cursor()
    
    update_fields = []
    update_values = []
    
    if nom:
        update_fields.append("nom = %s")
        update_values.append(nom)
    
    if prenom:
        update_fields.append("prenom = %s")
        update_values.append(prenom)
    
    if email:
        update_fields.append("email = %s")
        update_values.append(email)
    
    if mot_de_passe:
        hashed_password = hash_password(mot_de_passe)
        update_fields.append("mot_de_passe = %s")
        update_values.append(hashed_password)
    
    if not update_fields:
        cur.close()
        conn.close()
        raise ValueError("Aucun champ à mettre à jour")
    
    update_values.append(user_id)
    
    query = f"UPDATE utilisateur SET {', '.join(update_fields)} WHERE id = %s"
    cur.execute(query, tuple(update_values))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"status": "success", "id": user_id}

def user_delete(params):
    """Supprimer un utilisateur"""
    user_id = int(params.get("id"))
    
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM utilisateur WHERE id = %s", (user_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"status": "success", "id": user_id}

def check_auth(method, params):
    """Vérifie l'authentification pour les méthodes protégées"""
    public_methods = ["auth.login", "auth.logout"]
    
    if method in public_methods:
        return True
    
    token = params.get("_token") or params.get("token")
    
    if token == TOKENS.get("rpc"):
        return True
    
    if token in TOKENS:
        return True
    
    raise ValueError("Unauthorized")

# -----------------------------
# DISPATCH
# -----------------------------

def dispatch(method, params):
    # Vérifier l'authentification
    if method not in ["auth.login", "auth.logout"]:
        check_auth(method, params)
    
    if method == "auth.login":
        return auth.login(params)
    if method == "auth.logout":
        return auth.logout(params)
    
    if method == "stats.dashboard":
        return stats_dashboard()
    
    # COURSES
    if method == "course.list": return course_list()
    if method == "course.create": return course_create(params)
    if method == "course.update": return course_update(params)
    if method == "course.delete": return course_delete(params)
    
    # COURS (compatibilité)
    if method in ["cours.getAll", "cours.list", "cours.getall"]: 
        return cours_get_all(params)
    
    # STUDENTS
    if method == "student.list": return student_list(params)
    if method == "student.create": return student_create(params)
    if method == "student.update": return student_update(params)
    if method == "student.delete": return student_delete(params)
    
    # ABSENCES
    if method == "absence.getNonJustifiees":
        return student_absences_over_limit(params)
    
    # PLANNING
    if method == "planning.getDay": return planning_get_day(params)
    if method == "planning.getWeek": return planning_get_week(params)
    if method == "planning.generate": return planning_generate(params)
    
    # SÉANCES
    if method == "seance.add": return seance_add(params)
    if method == "seance.get": return seance_get(params)
    if method == "seance.update": return seance_update(params)
    if method == "seance.delete": return seance_delete(params)
    
    # GROUPES
    if method in ["groupe.getAll", "groupe.list", "groupe.getall", "group.list"]: 
        return groupe_get_all(params)
    
    # UTILITAIRES
    if method == "filiere.list": return filiere_list()
    if method == "promotion.list": return promotion_list()
    if method in ("professor.list", "prof.list"): return professor_list()
    
    # UTILISATEURS
    if method == "user.get": return user_get(params)
    if method == "user.update": return user_update(params)
    if method == "user.delete": return user_delete(params)
    
    raise ValueError(f"Method not found: {method}")

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/rpc":
            self.send_response(404); self.end_headers(); return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        
        method = "Inconnue"
        body = {}

        try:
            body = json.loads(raw)
            rpc_id = body.get("id")
            method = body.get("method")
            params = body.get("params", {}) or {}

            result = dispatch(method, params)
            response = ok(rpc_id, result)
            
        except Exception as e:
            print(f"\n[ERREUR SERVEUR RPC] Methode: {method} | Message: {str(e)}")
            
            rpc_id = body.get("id") if body else None
            response = err(rpc_id, -32000, str(e))

        out = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def main():
    print("RPC Server: http://127.0.0.1:8001/rpc")
    HTTPServer(("0.0.0.0", 8001), Handler).serve_forever()

if __name__ == "__main__":
    main()
=======
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
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
