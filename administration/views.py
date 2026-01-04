from datetime import date as dt_date
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpRequest, HttpResponseForbidden
from services.rpc_client import RpcError, JsonRpcClient
from services.db import get_conn
import time
from django.urls import reverse 
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from datetime import date, timedelta
from Home.decorators import auth_required_django
from debug_utils import debug_session, debug_request
import json
from .forms import AdminProfileForm
from services.rpc_server import TOKENS
import hashlib
import binascii
import os
from .rpc_services import COURSE_RPC, STUDENT_RPC, PLANNING_RPC

rpc_client = JsonRpcClient(
    "http://127.0.0.1:8001/rpc",
    headers={"Authorization": "Bearer mon_super_token_12345"}
)

def hash_password(password):
    """Fonction pour hasher les mots de passe dans Django"""
    salt = os.urandom(16).hex()
    hash_val = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        1000000
    )
    hash_hex = binascii.hexlify(hash_val).decode('utf-8')
    return f"pbkdf2_sha256$1000000${salt}${hash_hex}"

@auth_required_django(roles=["ADMINISTRATEUR"])
@debug_session 
def admin_profile(request):
    """Gérer le profil administrateur"""
    """Gérer le profil administrateur"""
    print("=== DEBUG: admin_profile view called ===")
    print(f"Session keys: {list(request.session.keys())}")
    print(f"User ID: {request.session.get('user_id')}")
    print(f"RPC Token exists: {'rpc_token' in request.session}")
    
    if "rpc_token" not in request.session:
        print("DEBUG: No rpc_token, redirecting to login")
        return redirect("/login/")
    
    token = request.session.get("rpc_token")
    user_id = request.session.get("user_id")
    
    if request.method == "POST":
        if "change_password" in request.POST:
            ancien = request.POST.get("ancien_motdepasse")
            nouveau = request.POST.get("nouveau_motdepasse")
            confirmation = request.POST.get("confirmation_motdepasse")
            
            if nouveau != confirmation:
                messages.error(request, "Les nouveaux mots de passe ne correspondent pas.")
            elif len(nouveau) < 8:
                messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
            else:
                try:
                    rpc_client.call("auth.login", {
                        "email": request.session.get("user_email"),
                        "motDePasse": ancien
                    })
                    
                    rpc_client.call("user.update", {
                        "_token": token,
                        "id": user_id,
                        "motDePasse": nouveau
                    })
                    
                    messages.success(request, "Mot de passe modifié avec succès !")
                    
                except RpcError as e:
                    messages.error(request, f"Ancien mot de passe incorrect : {str(e)}")
        else:
            nom = request.POST.get("nom")
            prenom = request.POST.get("prenom")
            email = request.POST.get("email")
            
            update_data = {
                "_token": token,
                "id": user_id,
            }
            
            if nom:
                update_data["nom"] = nom
            if prenom:
                update_data["prenom"] = prenom
            if email:
                update_data["email"] = email
            
            try:
                rpc_client.call("user.update", update_data)
                messages.success(request, "Profil mis à jour avec succès !")
            except RpcError as e:
                messages.error(request, f"Erreur : {str(e)}")
    
    try:
        user_info = rpc_client.call("user.get", {
            "_token": token,
            "id": user_id
        })
    except RpcError:
        user_info = {
            "id": user_id,
            "nom": request.session.get("user_nom"),
            "prenom": request.session.get("user_prenom"),
            "email": request.session.get("user_email"),
            "type_utilisateur": request.session.get("user_type"),
        }
    
    return render(request, "administration/admin_profile.html", {"user": user_info})

def admin_logout(request):
    """Déconnexion spécifique à l'administration"""
    token = request.session.get("rpc_token")
    if token and token in TOKENS:
        del TOKENS[token]
    
    request.session.flush()
    return redirect('accounts:login_page')

# ==========================
# Dashboard
# ==========================

def dashboard_stats():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM etudiant")
    students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM cours")
    courses = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM presence WHERE statut = 'ABSENT_NON_JUSTIFIE'")
    absences_nj = cur.fetchone()[0]

    cur.execute("""
        SELECT EXTRACT(WEEK FROM date_saisie) AS semaine, COUNT(*)
        FROM presence
        WHERE statut = 'ABSENT_NON_JUSTIFIE'
        GROUP BY semaine
        ORDER BY semaine
    """)
    weekly_raw = cur.fetchall()
    weekly = [{"week": int(w), "total": t} for w, t in weekly_raw]

    cur.execute("""
        SELECT f.nom, COUNT(*)
        FROM presence p
        JOIN etudiant e ON p.etudiant_id = e.id
        JOIN promotion pr ON e.promotion_id = pr.id
        JOIN filiere f ON pr.filiere_id = f.id
        WHERE p.statut = 'ABSENT_NON_JUSTIFIE'
        GROUP BY f.nom
        ORDER BY f.nom
    """)
    filiere_raw = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "students": students,
        "courses": courses,
        "absences_nj": absences_nj,
        "weekly": weekly,
        "absences_par_filiere": {
            "labels": [row[0] for row in filiere_raw],
            "data": [row[1] for row in filiere_raw]
        }
    }

@auth_required_django(roles=["ADMINISTRATEUR"])
def admin_dashboard(request):
    """Dashboard administrateur - VUE SIMPLIFIÉE"""
    # Vérifier la session (simple vérification)
    if not request.session.get('logged_in'):
        return redirect('/login/')
    
    # Vérifier le rôle
    if request.session.get('user_role') != 'ADMINISTRATEUR':
        return redirect('/login/')
    
    # Récupérer les stats pour le dashboard
    stats = dashboard_stats()  # Votre fonction existante
    
    context = {
        'user': {
            'nom': request.session.get('user_nom'),
            'prenom': request.session.get('user_prenom'),
            'email': request.session.get('user_email'),
            'role': request.session.get('user_role')
        },
        'stats': stats
    }
    
    return render(request, 'administration/dashboard.html', context)

# ==========================
# Courses
# ==========================
@auth_required_django(roles=["ADMINISTRATEUR"])
def cours_list(request: HttpRequest):
    error = None
    courses = []
    profs = []
    
    try:
        print("[DEBUG] Récupération des cours...")
        courses = COURSE_RPC.call("course.list", {})
        print(f"[DEBUG] {len(courses)} cours récupérés")
        
        # Debug: afficher la structure des cours
        if courses:
            print("[DEBUG] Structure du premier cours:")
            print(courses[0])
        
        # Récupérer les professeurs
        print("[DEBUG] Récupération des professeurs...")
        profs = COURSE_RPC.call("professor.list", {})
        print(f"[DEBUG] {len(profs)} professeurs récupérés")
        
        # Créer un mapping robuste des profs
        prof_dict = {}
        for p in profs:
            # Normaliser l'ID
            prof_id = p.get('id')
            if not prof_id:
                continue
            
            # Construire le nom complet
            if p.get('fullName'):
                nom_complet = p['fullName']
            elif p.get('nom_complet'):
                nom_complet = p['nom_complet']
            elif p.get('prenom') and p.get('nom'):
                nom_complet = f"{p['prenom']} {p['nom']}"
            elif p.get('nom'):
                nom_complet = p['nom']
            elif p.get('prenom'):
                nom_complet = p['prenom']
            else:
                nom_complet = f"Professeur #{prof_id}"
            
            prof_dict[prof_id] = nom_complet
        
        print(f"[DEBUG] Dictionnaire profs créé: {len(prof_dict)} entrées")
        print(f"[DEBUG] Exemples de profs dans le dict: {list(prof_dict.items())[:3]}")
        
        # Ajouter le nom du professeur à chaque cours
        for course in courses:
            # Chercher l'ID du professeur dans différentes clés possibles
            prof_id_course = None
            
            # Vérifier d'abord si le cours a déjà un nom de professeur
            if 'profFullName' in course and course['profFullName']:
                print(f"[DEBUG] Cours {course.get('id')} a déjà profFullName: {course['profFullName']}")
                continue
            
            # Essayer différentes clés
            keys_to_check = ['professorId', 'professeurId', 'professor_id', 'professeur_id', 'profId']
            
            for key in keys_to_check:
                if key in course and course[key]:
                    prof_id_course = course[key]
                    print(f"[DEBUG] Cours {course.get('id')} - Prof ID trouvé dans '{key}': {prof_id_course}")
                    break
            
            # Si aucune clé standard ne fonctionne, chercher dans les clés disponibles
            if prof_id_course is None:
                for key, value in course.items():
                    if 'prof' in key.lower() and value and key not in keys_to_check:
                        print(f"[DEBUG] Cours {course.get('id')} - Prof trouvé dans clé non standard '{key}': {value}")
                        prof_id_course = value
                        break
            
            # Trouver le nom du professeur
            if prof_id_course and str(prof_id_course) in prof_dict:
                course['profFullName'] = prof_dict[str(prof_id_course)]
                print(f"[DEBUG] Cours {course.get('id')} - Nom prof assigné: {prof_dict[str(prof_id_course)]}")
            elif prof_id_course:
                # L'ID existe mais pas dans le dictionnaire
                course['profFullName'] = f"Professeur #{prof_id_course}"
                print(f"[DEBUG] Cours {course.get('id')} - Prof ID {prof_id_course} non trouvé dans dict")
            else:
                course['profFullName'] = "--"
                print(f"[DEBUG] Cours {course.get('id')} - Aucun prof trouvé")
                
    except RpcError as e:
        error = f"Erreur RPC: {str(e)}"
        print(f"[ERROR] {error}")
    except Exception as e:
        error = f"Erreur générale: {str(e)}"
        print(f"[ERROR] {error}")
        import traceback
        traceback.print_exc()
    
    return render(request, "administration/cours_list.html", {
        "courses": courses,
        "profs": profs,
        "error": error
    })
@auth_required_django(roles=["ADMINISTRATEUR"])
def cours_create(request: HttpRequest):
    error = None
    try:
        profs = COURSE_RPC.call("professor.list", {})
    except Exception as e:
        profs = []
        error = str(e)

    if request.method == "POST":
        prof_id_raw = request.POST.get("professorId") or ""
        prof_id = int(prof_id_raw) if prof_id_raw else None

        payload = {
            "code": request.POST.get("code", "").strip(),
            "libelle": request.POST.get("libelle", "").strip(),
            "volumeHoraire": int(request.POST.get("volumeHoraire", "0") or 0),
            "professorId": prof_id,
        }

        try:
            created = COURSE_RPC.call("course.create", {
                "code": payload["code"],
                "libelle": payload["libelle"],
                "volumeHoraire": payload["volumeHoraire"],
            })

            if prof_id is not None:
                COURSE_RPC.call("course.update", {"id": int(created["id"]), "professorId": prof_id})

            return redirect("administration:cours_list")
        except Exception as e:
            error = str(e)
            return render(request, "administration/cours_list.html", {
                "mode": "create",
                "error": error,
                "course": payload,
                "profs": profs
            })

    return render(request, "administration/cours_list.html", {
        "mode": "create",
        "error": error,
        "course": {"code": "", "libelle": "", "volumeHoraire": "", "professorId": ""},
        "profs": profs
    })


@auth_required_django(roles=["ADMINISTRATEUR"])
def cours_edit(request, pk):
    pk = int(pk)
    try:
        profs = COURSE_RPC.call("professor.list", {})
    except Exception as e:
        profs = []
        print(f"Erreur RPC profs: {e}")

    # Récupérer tous les cours
    try:
        courses = COURSE_RPC.call("course.list", {})
    except Exception:
        courses = []
    
    # Trouver le cours à modifier
    course = None
    for c in courses:
        if int(c.get("id", 0)) == pk:
            course = c
            break
    
    if not course:
        messages.error(request, "Cours introuvable", extra_tags="cours_error")
        return redirect("administration:cours_list")

    if request.method == "POST":
        prof_id_raw = request.POST.get("professorId") or ""
        prof_id = int(prof_id_raw) if prof_id_raw else None

        payload = {
            "id": pk,
            "code": request.POST.get("code", "").strip(),
            "libelle": request.POST.get("libelle", "").strip(),
            "volumeHoraire": int(request.POST.get("volume_horaire", "0") or 0),
            "professorId": prof_id,
        }

        try:
            COURSE_RPC.call("course.update", payload)
            messages.success(request, "Cours modifié avec succès", extra_tags="cours_modif_success")
            return redirect("administration:cours_list")
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}", extra_tags="cours_error")
            # Retourner à la liste avec les données actuelles
            return render(request, "administration/cours_list.html", {
                "courses": courses,
                "profs": profs,
                "edit_course_id": pk,
                "form_data": payload
            })

    # GET request - afficher la liste avec le formulaire pré-rempli
    return render(request, "administration/cours_list.html", {
        "courses": courses,
        "profs": profs,
        "edit_course_id": pk,
        "form_data": course
    })

@auth_required_django(roles=["ADMINISTRATEUR"])
def cours_delete(request: HttpRequest, course_id: int):
    if request.method == "POST":
        try:
            COURSE_RPC.call("course.delete", {"id": course_id})
        except Exception:
            pass
        return redirect("administration:cours_list")

    return render(request, "administration/confirm_delete.html", {
        "title": "Supprimer cours",
        "message": f"Voulez-vous supprimer le cours #{course_id} ?",
        "cancel_url": "administration:cours_list",
    })

# ==========================
# Students
# ==========================

@auth_required_django(roles=["ADMINISTRATEUR"])
def student_list(request: HttpRequest):
    error = None
    students = []
    promo = request.GET.get("promotionId")
    filiere = request.GET.get("filiereId")

    try:
        params = {}
        if promo:
            params["promotionId"] = int(promo)
        if filiere:
            params["filiereId"] = int(filiere)

        students = STUDENT_RPC.call("student.list", params)
        filieres = STUDENT_RPC.call("filiere.list")
        promotions = STUDENT_RPC.call("promotion.list")

        promo_dict = {p["id"]: p["libelle"] for p in promotions}
        for s in students:
            s["promotionLibelle"] = promo_dict.get(s["promotionId"], f"ID {s['promotionId']}")
    except Exception as e:
        error = str(e)
        filieres = promotions = []
        students = []

    return render(request, "administration/student_list.html", {
        "students": students,
        "error": error,
        "filieres": filieres,
        "promotions": promotions,
        "selected_promo": int(promo) if promo else None,
        "selected_filiere": int(filiere) if filiere else None
    })
@auth_required_django(roles=["ADMINISTRATEUR"])
def student_create(request: HttpRequest):
    error = None
    filieres = []
    promotions = []

    try:
        filieres = STUDENT_RPC.call("filiere.list")
        promotions = STUDENT_RPC.call("promotion.list")
    except Exception as e:
        error = str(e)

    if request.method == "POST":
        try:
            # CORRECTION : Utiliser les bons noms de champs
            nom = request.POST.get("nom", "").strip()
            prenom = request.POST.get("prenom", "").strip()
            email = request.POST.get("email", "").strip()
            promotion_id = request.POST.get("promotion_id", "").strip()
            filiere_id = request.POST.get("filiere_id", "").strip()
            code_etudiant = request.POST.get("code_etudiant", "").strip()
            mot_de_passe = request.POST.get("password", "").strip()
            
            # Validation
            if not all([nom, prenom, email, promotion_id, filiere_id, code_etudiant, mot_de_passe]):
                error = "Tous les champs sont obligatoires"
            else:
                # CORRECTION : Envoyer les bons noms au RPC
                result = STUDENT_RPC.call("student.create", {
                    "nom": nom,
                    "prenom": prenom,
                    "email": email,
                    "promotionId": int(promotion_id),
                    "filiereId": int(filiere_id),  # Ajouter filiereId si nécessaire
                    "codeEtudiant": code_etudiant,
                    "motDePasse": mot_de_passe,
                })
                
                messages.success(request, "Étudiant créé avec succès", extra_tags="etudiant_success")
                return redirect("administration:student_list")
                
        except Exception as e:
            error = str(e)
            messages.error(request, f"Erreur: {error}", extra_tags="etudiant_error")

    return render(request, "administration/student_list.html", {
        "mode": "create",
        "error": error,
        "student": {"nom": "", "prenom": "", "email": "", "promotionId": "", "codeEtudiant": "", "motDePasse": ""},
        "filieres": filieres,
        "promotions": promotions,
    })
@auth_required_django(roles=["ADMINISTRATEUR"])
def student_edit(request: HttpRequest, student_id: int):
    try:
        # Récupérer les données initiales
        students = STUDENT_RPC.call("student.list", {})
        student = next((s for s in students if s["id"] == student_id), None)
        if not student:
            messages.error(request, "Étudiant introuvable")
            return redirect("administration:student_list")
            
        filieres = STUDENT_RPC.call("filiere.list")
        promotions = STUDENT_RPC.call("promotion.list")
        
        if request.method == "POST":
            try:
                # CORRECTION : Utiliser les bons noms de champs
                promotion_id = request.POST.get("promotion_id", "").strip()
                filiere_id = request.POST.get("filiere_id", "").strip()
                
                # Validation
                if not promotion_id:
                    messages.error(request, "Promotion requise", extra_tags="etudiant_modif_error")
                    raise ValueError("Promotion requise")
                
                if not filiere_id:
                    messages.error(request, "Filière requise", extra_tags="etudiant_modif_error")
                    raise ValueError("Filière requise")
                
                # Préparer les données de modification
                payload = {
                    "id": student_id,
                    "nom": request.POST.get("nom", "").strip(),
                    "prenom": request.POST.get("prenom", "").strip(),
                    "email": request.POST.get("email", "").strip(),
                    "promotionId": int(promotion_id),  # CORRECTION
                    "filiereId": int(filiere_id),      # CORRECTION
                    "codeEtudiant": request.POST.get("code_etudiant", "").strip(),
                }
                
                # Vérifier le mot de passe
                mp = request.POST.get("motDePasse", "").strip()
                if mp:
                    payload["motDePasse"] = mp
                
                # Debug: afficher ce qui est envoyé
                print(f"Payload envoyé: {payload}")
                
                # Appeler le service
                result = STUDENT_RPC.call("student.update", payload)
                print(f"Résultat de l'update: {result}")
                
                # Message de succès et redirection
                messages.success(request, "Étudiant modifié avec succès", extra_tags="etudiant_modif_success")
                return redirect("administration:student_list")
                
            except ValueError as ve:
                messages.error(request, str(ve), extra_tags="etudiant_modif_error")
                return render(request, "administration/student_list.html", {
                    "students": STUDENT_RPC.call("student.list", {}),
                    "filieres": filieres,
                    "promotions": promotions,
                    "student": student,
                    "selected_filiere": None,
                    "selected_promo": None,
                })
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}", extra_tags="etudiant_modif_error")
                return render(request, "administration/student_list.html", {
                    "students": STUDENT_RPC.call("student.list", {}),
                    "filieres": filieres,
                    "promotions": promotions,
                    "student": student,
                    "selected_filiere": None,
                    "selected_promo": None,
                })
        
        # GET request
        return render(request, "administration/student_list.html", {
            "students": students,
            "filieres": filieres,
            "promotions": promotions,
            "student": student,
            "selected_filiere": None,
            "selected_promo": None,
            "editing": True,
        })
        
    except Exception as e:
        messages.error(request, f"Erreur système: {str(e)}")
        return redirect("administration:student_list")
    

@auth_required_django(roles=["ADMINISTRATEUR"])
def student_delete(request: HttpRequest, student_id: int):
    if request.method == "POST":
        try:
            STUDENT_RPC.call("student.delete", {"id": student_id})
        except Exception:
            pass
        return redirect("administration:student_list")

# ==========================
# Absences avec filtres
# ==========================

@auth_required_django(roles=["ADMINISTRATEUR"])
def students_absences(request: HttpRequest):
    """Afficher les étudiants avec plus de X absences dans un même cours - SANS FILTRE COURS"""
    error = None
    absences_data = []
    filieres = []
    
    try:
        # Récupérer les paramètres (ONLY limit et filière)
        limit = int(request.GET.get("limit", 3))
        filiere_id = request.GET.get("filiere")
        
        print(f"\n[VIEW] Filtres: limit={limit}, filiere={filiere_id}")
        
        # Préparer les paramètres RPC (PAS DE coursId)
        params = {"limit": limit}
        if filiere_id:
            params["filiereId"] = int(filiere_id)
        
        # Appeler le RPC
        absences_data = STUDENT_RPC.call("absence.getNonJustifiees", params)
        
        print(f"[VIEW] {len(absences_data)} résultats obtenus")
        
        # Récupérer seulement les filières pour le filtre
        filieres = STUDENT_RPC.call("filiere.list")
        
    except RpcError as e:
        error = str(e)
        print(f"[ERROR] RPC: {e}")
    except Exception as e:
        error = f"Erreur: {str(e)}"
        import traceback
        traceback.print_exc()
    
    return render(request, "administration/students_absences.html", {
        "absences": absences_data,
        "error": error,
        "limit": limit,
        "filieres": filieres,
        "selected_filiere": int(filiere_id) if filiere_id else None,
        # SUPPRIMER: selected_cours
    })
# ==========================
# Planning
# ==========================

@auth_required_django(roles=["ADMINISTRATEUR"])
def planning_home(request: HttpRequest):
    return render(request, "administration/planning_home.html")

@auth_required_django(roles=["ADMINISTRATEUR"])
def planning_day(request: HttpRequest):
    error = None
    sessions = []
    date = request.GET.get("date", "")

    if date:
        try:
            sessions = PLANNING_RPC.call("planning.getDay", {"date": date})
        except Exception as e:
            error = str(e)

    return render(request, "administration/planning_day.html", {"sessions": sessions, "date": date, "error": error})
def get_seances_from_db(week, year):
    """Récupérer les séances directement depuis la base de données"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            # Requête principale pour récupérer les séances de la semaine
            cur.execute("""
                SELECT 
                    s.id,
                    s.date,
                    s.heure_debut,
                    s.heure_fin,
                    s.salle,
                    s.cours_id,
                    s.groupe_id,
                    s.planning_id,
                    c.code as cours_code,
                    c.libelle as cours_libelle,
                    c.volume_horaire,
                    u_prof.nom as prof_nom,
                    u_prof.prenom as prof_prenom,
                    g.nom as groupe_nom,
                    p.id as promotion_id,
                    p.libelle as promotion_libelle,
                    p.annee_scolaire,
                    f.id as filiere_id,
                    f.code as filiere_code,
                    f.nom as filiere_nom
                FROM seance s
                LEFT JOIN cours c ON s.cours_id = c.id
                LEFT JOIN utilisateur u_prof ON c.professeur_id = u_prof.id
                LEFT JOIN groupe g ON s.groupe_id = g.id
                LEFT JOIN promotion p ON g.promotion_id = p.id
                LEFT JOIN filiere f ON p.filiere_id = f.id
                WHERE EXTRACT(WEEK FROM s.date) = %s 
                  AND EXTRACT(YEAR FROM s.date) = %s
                ORDER BY s.date, s.heure_debut
            """, [week, year])
            
            rows = cur.fetchall()
            
            # Structure des données
            sessions = []
            for row in rows:
                session = {
                    "id": row[0],
                    "date": row[1],
                    "heureDebut": row[2],
                    "heureFin": row[3],
                    "salle": row[4],
                    "cours_id": row[5],
                    "groupe_id": row[6],
                    "planning_id": row[7],
                    "cours": {
                        "id": row[5],
                        "code": row[8],
                        "libelle": row[9],
                        "volumeHoraire": row[10],
                        "professeur_nom": f"{row[11]} {row[12]}" if row[11] and row[12] else None
                    } if row[8] else None,
                    "groupe_nom": row[13],
                    "promotion": {
                        "id": row[14],
                        "libelle": row[15],
                        "annee": row[16]
                    } if row[14] else None,
                    "filiere": {
                        "id": row[17],
                        "code": row[18],
                        "nom": row[19]
                    } if row[17] else None
                }
                sessions.append(session)
            
            return sessions
            
    except Exception as e:
        print(f"[ERROR] Erreur récupération séances depuis BD: {e}")
        return []
    
@auth_required_django(roles=["ADMINISTRATEUR"])
def planning_week(request):
    """Planning semaine avec données directement depuis la base de données"""
    # Utiliser la semaine/année courantes par défaut
    today = date.today()
    current_iso = today.isocalendar()
    week_raw = request.GET.get('week', current_iso[1])
    year_raw = request.GET.get('year', current_iso[0])
    weekpicker_raw = request.GET.get('weekpicker', '').strip()
    
    # Traitement du weekpicker
    if weekpicker_raw:
        import re
        m = re.match(r'^(?P<y>\d{4})-W?(?P<w>\d{1,2})$', weekpicker_raw)
        if m:
            try:
                week = int(m.group('w'))
                year = int(m.group('y'))
            except Exception:
                week = current_iso[1]
                year = current_iso[0]
        else:
            week = current_iso[1]
            year = current_iso[0]
    else:
        try:
            week = int(week_raw)
        except (TypeError, ValueError):
            week = current_iso[1]

        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            year = current_iso[0]
    
    # Validation de la semaine
    try:
        max_week = date(year, 12, 28).isocalendar()[1]
    except Exception:
        max_week = 52

    if week < 1 or week > max_week:
        week = min(max_week, max(1, week))
    
    # Récupération des séances depuis la base de données
    sessions = get_seances_from_db(week, year)
    print(f"[DEBUG] {len(sessions)} séances récupérées de la BD pour semaine {week}/{year}")
    
    # Calcul des dates de la semaine
    try:
        monday = date.fromisocalendar(year, week, 1)
        sunday = monday + timedelta(days=6)
    except Exception:
        monday = date.today()
        sunday = monday + timedelta(days=6)
    
    # Navigation semaine précédente/suivante
    prev_monday = monday - timedelta(days=7)
    next_monday = monday + timedelta(days=7)
    prev_week = prev_monday.isocalendar()[1]
    prev_year = prev_monday.isocalendar()[0]
    next_week = next_monday.isocalendar()[1]
    next_year = next_monday.isocalendar()[0]
    
    # Préparation des dates de la semaine
    week_dates = []
    for i in range(7):
        day_date = monday + timedelta(days=i)
        week_dates.append({
            'date': day_date,
            'name': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][i],
            'date_iso': day_date.isoformat()
        })
    
    # Grouper les sessions par jour
    sessions_by_day = {}
    for session in sessions:
        raw_date = session.get('date')
        if isinstance(raw_date, str):
            day_iso = raw_date
        elif hasattr(raw_date, 'isoformat'):
            day_iso = raw_date.isoformat()
        else:
            try:
                day_iso = date.fromisoformat(str(raw_date)).isoformat()
            except Exception:
                continue
        
        sessions_by_day.setdefault(day_iso, []).append(session)
    
    # Tri des sessions par heure
    for day_iso in sessions_by_day:
        sessions_by_day[day_iso].sort(key=lambda s: s.get('heureDebut', ''))
    
    # Construction de la structure finale
    days_with_sessions = []
    for day in week_dates:
        day_iso = day['date_iso']
        sessions_for_day = sessions_by_day.get(day_iso, [])
        
        days_with_sessions.append({
            'name': day['name'],
            'date': day['date'],
            'date_iso': day_iso,
            'sessions': sessions_for_day
        })
    
    # Valeur pour le weekpicker
    weekpicker_value = f"{year}-W{week:02d}"
    
    context = {
        'week': week,
        'year': year,
        'monday': monday,
        'sunday': sunday,
        'prev_week': prev_week,
        'prev_year': prev_year,
        'next_week': next_week,
        'next_year': next_year,
        'weekpicker_value': weekpicker_value,
        'days_with_sessions': days_with_sessions,
        'raw_sessions': sessions,  # Pour debug
    }
    
    return render(request, 'administration/planning_week.html', context)

@auth_required_django(roles=["ADMINISTRATEUR"])
def planning_week_raw(request):
    """Return raw RPC planning.getWeek JSON for debugging"""
    week = int(request.GET.get('week', date.today().isocalendar()[1]))
    year = int(request.GET.get('year', date.today().isocalendar()[0]))
    try:
        sessions = PLANNING_RPC.call("planning.getWeek", {"week": week, "year": year})
        return JsonResponse({"week": week, "year": year, "sessions": sessions}, json_dumps_params={"indent": 2})
    except RpcError as e:
        return JsonResponse({"error": str(e)}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
@auth_required_django(roles=["ADMINISTRATEUR"])
def seance_add(request):
    """Formulaire d'ajout de séance avec validation complète"""
    week = int(request.GET.get('week', 1))
    year = int(request.GET.get('year', date.today().year))
    prefilled_date = request.GET.get('date', '')

    # Défaut pour la semaine/année de la date
    week_for_date = week
    year_for_date = year
    
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    
    # Récupérer les listes pour les selects
    cours_list = get_courses_with_professors()
    professeurs = get_professeurs()
    groupes = get_groupes_with_promotions()
    filieres = get_filieres()
    promotions = get_promotions()
    
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            date_val = request.POST.get('date', '').strip()
            heure_debut = request.POST.get('heure_debut', '').strip()
            heure_fin = request.POST.get('heure_fin', '').strip()
            salle = request.POST.get('salle', '').strip()
            cours_raw = request.POST.get('cours_id', '').strip()
            groupe_raw = request.POST.get('groupe_id', '').strip()
            professeur_raw = request.POST.get('professeur_id', '').strip()
            
            # Validation des champs obligatoires
            errors = []
            
            if not date_val:
                errors.append("La date est obligatoire")
            
            if not heure_debut:
                errors.append("L'heure de début est obligatoire")
            
            if not heure_fin:
                errors.append("L'heure de fin est obligatoire")
            
            if not salle:
                errors.append("La salle est obligatoire")
            
            if not cours_raw:
                errors.append("Le cours est obligatoire")
            
            if not groupe_raw:
                errors.append("Le groupe est obligatoire")
            
            if errors:
                raise ValueError(" | ".join(errors))
            
            # Valider que l'heure de début < heure de fin
            if heure_debut and heure_fin and heure_debut >= heure_fin:
                raise ValueError("L'heure de début doit être antérieure à l'heure de fin")
            
            # Déterminer la semaine et l'année à partir de la date
            try:
                date_obj = date.fromisoformat(date_val)
                week_for_date = date_obj.isocalendar()[1]
                year_for_date = date_obj.isocalendar()[0]
            except Exception:
                raise ValueError("La date fournie est invalide (format: AAAA-MM-JJ)")
            
            # Récupérer ou créer le planning correspondant
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT id FROM planning 
                    WHERE semaine = %s AND annee = %s
                    LIMIT 1
                """, (week_for_date, year_for_date))

                row = cur.fetchone()

                if row:
                    planning_id = row[0]
                else:
                    # Créer un nouveau planning
                    cur.execute("""
                        INSERT INTO planning(semaine, annee, administrateur_id, date_creation)
                        VALUES (%s, %s, %s, NOW()) 
                        RETURNING id
                    """, (week_for_date, year_for_date, request.session.get('user_id', 1)))
                    planning_id = cur.fetchone()[0]
            
            # Conversion des IDs
            try:
                cours_id = int(cours_raw)
            except (ValueError, TypeError):
                raise ValueError("Veuillez sélectionner un cours valide")
            
            try:
                groupe_id = int(groupe_raw)
            except (ValueError, TypeError):
                raise ValueError("Veuillez sélectionner un groupe valide")
            
            # Vérifier si le groupe existe
            with connection.cursor() as cur:
                cur.execute("SELECT id FROM groupe WHERE id = %s", [groupe_id])
                if not cur.fetchone():
                    raise ValueError(f"Le groupe #{groupe_id} n'existe pas")
            
            # Si un professeur est sélectionné, mettre à jour le cours
            if professeur_raw:
                try:
                    professeur_id = int(professeur_raw)
                    # Vérifier si le professeur existe
                    with connection.cursor() as cur:
                        cur.execute("SELECT id FROM utilisateur WHERE id = %s AND type_utilisateur IN ('PROFESSEUR', 'ENSEIGNANT')", [professeur_id])
                        if cur.fetchone():
                            # Mettre à jour le professeur du cours
                            COURSE_RPC.call("course.update", {
                                "id": cours_id,
                                "professorId": professeur_id
                            })
                except (ValueError, TypeError):
                    # Le professeur n'est pas obligatoire, on continue sans erreur
                    pass
            
            # Vérifier s'il n'y a pas de conflit de salle/heure
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM seance 
                    WHERE date = %s 
                    AND salle = %s 
                    AND (
                        (%s < heure_fin AND %s > heure_debut)
                        OR heure_debut = %s
                    )
                """, [date_val, salle, heure_debut, heure_fin, heure_debut])
                
                conflit_count = cur.fetchone()[0]
                if conflit_count > 0:
                    raise ValueError(f"Conflit détecté : la salle {salle} est déjà occupée à cet horaire")
            
            # Préparation des paramètres pour le RPC
            params = {
                "date": date_val,
                "heure_debut": heure_debut,
                "heure_fin": heure_fin,
                "salle": salle,
                "cours": cours_id,
                "groupe": groupe_id,
                "planning_id": planning_id
            }
            
            # Appel RPC pour créer la séance
            result = PLANNING_RPC.call("seance.add", params)
            
            messages.success(request, f"✅ Séance ajoutée avec succès (ID: {result.get('id')})")
            
            # Redirection vers le planning avec rafraîchissement forcé
            redirect_url = f'/administration/planning/week/?week={week_for_date}&year={year_for_date}&t={int(time.time())}'
            response = redirect(redirect_url)
            
            # Empêcher la mise en cache
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            return response
            
        except RpcError as e:
            error_msg = f"Erreur serveur: {str(e)}"
        except ValueError as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f"Erreur inattendue: {str(e)}"
            import traceback
            traceback.print_exc()
        
        # En cas d'erreur, recalculer les dates
        try:
            if 'date_val' in locals() and date_val:
                date_obj = date.fromisoformat(date_val)
                week_for_date = date_obj.isocalendar()[1]
                year_for_date = date_obj.isocalendar()[0]
                monday = date.fromisocalendar(year_for_date, week_for_date, 1)
                sunday = monday + timedelta(days=6)
        except:
            pass
        
        # En cas d'erreur, conserver les données soumises
        form_data = {
            'date': request.POST.get('date', prefilled_date),
            'heure_debut': request.POST.get('heure_debut', ''),
            'heure_fin': request.POST.get('heure_fin', ''),
            'salle': request.POST.get('salle', ''),
            'cours_id': request.POST.get('cours_id', ''),
            'groupe_id': request.POST.get('groupe_id', ''),
            'professeur_id': request.POST.get('professeur_id', ''),
            'filiere_id': request.POST.get('filiere_id', ''),
            'promotion_id': request.POST.get('promotion_id', '')
        }
        
        return render(request, 'administration/seance_add.html', {
            'week': week_for_date,
            'year': year_for_date,
            'monday': monday,
            'sunday': sunday,
            'prefilled_date': request.POST.get('date', prefilled_date),
            'error': error_msg,
            'cours_list': cours_list,
            'professeurs': professeurs,
            'groupes': groupes,
            'filieres': filieres,
            'promotions': promotions,
            'form_data': form_data
        })
    
    # GET request: afficher le formulaire vide ou pré-rempli
    form_data = {
        'date': prefilled_date,
        'heure_debut': '08:00',
        'heure_fin': '10:00',
        'salle': '',
        'cours_id': '',
        'groupe_id': '',
        'professeur_id': '',
        'filiere_id': '',
        'promotion_id': ''
    }
    
    return render(request, 'administration/seance_add.html', {
        'week': week,
        'year': year,
        'monday': monday,
        'sunday': sunday,
        'prefilled_date': prefilled_date,
        'cours_list': cours_list,
        'professeurs': professeurs,
        'groupes': groupes,
        'filieres': filieres,
        'promotions': promotions,
        'form_data': form_data
    })
def get_seances_from_db_enhanced(week, year):
    """Récupérer les séances avec toutes les informations nécessaires"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            # Requête optimisée pour récupérer TOUTES les informations
            cur.execute("""
                SELECT 
                    s.id,
                    s.date,
                    s.heure_debut,
                    s.heure_fin,
                    s.salle,
                    s.cours_id,
                    s.groupe_id,
                    s.planning_id,
                    
                    -- Informations du cours
                    c.code as cours_code,
                    c.libelle as cours_libelle,
                    c.volume_horaire,
                    c.professeur_id as cours_professeur_id,
                    
                    -- Informations du professeur
                    u_prof.id as prof_id,
                    u_prof.nom as prof_nom,
                    u_prof.prenom as prof_prenom,
                    u_prof.email as prof_email,
                    
                    -- Informations du groupe
                    g.nom as groupe_nom,
                    g.promotion_id,
                    
                    -- Informations de la promotion
                    p.libelle as promotion_libelle,
                    p.annee_scolaire,
                    p.filiere_id,
                    
                    -- Informations de la filière
                    f.code as filiere_code,
                    f.nom as filiere_nom
                    
                FROM seance s
                
                -- Jointure avec le cours
                LEFT JOIN cours c ON s.cours_id = c.id
                
                -- Jointure avec le professeur (directement depuis utilisateur)
                LEFT JOIN utilisateur u_prof ON c.professeur_id = u_prof.id
                
                -- Jointure avec le groupe
                LEFT JOIN groupe g ON s.groupe_id = g.id
                
                -- Jointure avec la promotion
                LEFT JOIN promotion p ON g.promotion_id = p.id
                
                -- Jointure avec la filière
                LEFT JOIN filiere f ON p.filiere_id = f.id
                
                WHERE EXTRACT(WEEK FROM s.date) = %s 
                  AND EXTRACT(YEAR FROM s.date) = %s
                ORDER BY s.date, s.heure_debut
            """, [week, year])
            
            rows = cur.fetchall()
            
            # Structure des données
            sessions = []
            for row in rows:
                # Construire le nom du professeur
                professeur_nom = None
                if row[12] and row[13]:  # prof_nom et prof_prenom
                    professeur_nom = f"{row[12]} {row[13]}"
                elif row[12]:
                    professeur_nom = row[12]
                elif row[13]:
                    professeur_nom = row[13]
                
                # Si pas de professeur dans la jointure, essayer de le récupérer
                if not professeur_nom and row[10]:  # cours_professeur_id
                    professeur_info = get_professeur_by_id(row[10])
                    if professeur_info:
                        professeur_nom = professeur_info.get('nom_complet')
                
                # Construire les informations du cours
                cours_info = None
                if row[5]:  # cours_id existe
                    cours_info = {
                        "id": row[5],
                        "code": row[8] or f"COURS_{row[5]}",
                        "libelle": row[9] or "Cours sans nom",
                        "volumeHoraire": row[10] or 0,
                        "professeur_id": row[11],
                        "professeur_nom": professeur_nom or "Non assigné"
                    }
                
                # Construire les informations de la filière
                filiere_info = None
                if row[21]:  # filiere_code
                    filiere_info = {
                        "id": row[18],  # filiere_id
                        "code": row[21] or "",
                        "nom": row[22] or ""
                    }
                
                # Construire les informations de la promotion
                promotion_info = None
                if row[16]:  # promotion_libelle
                    promotion_info = {
                        "id": row[15],  # promotion_id
                        "libelle": row[16] or "",
                        "annee": row[17] or ""
                    }
                
                session = {
                    "id": row[0],
                    "date": row[1],
                    "heure_debut": row[2],
                    "heure_fin": row[3],
                    "heureDebut": row[2],
                    "heureFin": row[3],
                    "salle": row[4] or "Non définie",
                    "cours_id": row[5],
                    "groupe_id": row[6],
                    "planning_id": row[7],
                    
                    # Cours complet
                    "cours": cours_info,
                    
                    # Professeur séparé
                    "professeur_nom": professeur_nom,
                    "professeur_id": row[11],  # cours_professeur_id
                    
                    # Groupe
                    "groupe_nom": row[14] or f"Groupe {row[6]}" if row[6] else "Non défini",
                    
                    # Promotion
                    "promotion": promotion_info,
                    "promotion_libelle": row[16] if row[16] else None,
                    "promotion_id": row[15],
                    
                    # Filière
                    "filiere": filiere_info,
                    "filiere_nom": row[22] if row[22] else None,
                    "filiere_code": row[21] if row[21] else None
                }
                sessions.append(session)
            
            print(f"[DEBUG] {len(sessions)} séances enrichies pour semaine {week}/{year}")
            return sessions
            
    except Exception as e:
        print(f"[ERROR] Erreur récupération séances: {e}")
        import traceback
        traceback.print_exc()
        return []
def get_professeur_by_id(professeur_id):
    """Récupérer un professeur par son ID"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT id, nom, prenom, email
                FROM utilisateur
                WHERE id = %s AND type_utilisateur IN ('PROFESSEUR', 'ENSEIGNANT')
            """, [professeur_id])
            
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "nom": row[1],
                    "prenom": row[2],
                    "email": row[3],
                    "nom_complet": f"{row[1]} {row[2]}"
                }
        return None
    except Exception as e:
        print(f"[ERROR] Erreur récupération professeur {professeur_id}: {e}")
        return None
    
def get_courses_with_professors():
    """Récupérer la liste des cours avec les noms des professeurs"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.code, c.libelle, c.volume_horaire,
                       u.id as prof_id, u.nom as prof_nom, u.prenom as prof_prenom
                FROM cours c
                LEFT JOIN utilisateur u ON c.professeur_id = u.id
                ORDER BY c.code
            """)
            rows = cur.fetchall()
            
            courses = []
            for r in rows:
                # CONVERTIR L'ID EN ENTIER POUR ÊTRE SÛR
                try:
                    course_id = int(r[0])
                except:
                    course_id = r[0]
                    
                try:
                    prof_id = int(r[4]) if r[4] else None
                except:
                    prof_id = r[4] if r[4] else None
                
                course = {
                    "id": course_id,  # ID comme entier
                    "code": r[1],
                    "libelle": r[2],
                    "volumeHoraire": r[3],
                    "professeur_id": prof_id,  # ID comme entier ou None
                    "professeur_nom": f"{r[5]} {r[6]}" if r[5] and r[6] else "Non assigné"
                }
                courses.append(course)
            
            print(f"[DEBUG] {len(courses)} cours chargés, exemples: {courses[:3]}")
            return courses
    except Exception as e:
        print(f"[ERROR] Erreur récupération cours: {e}")
        return []
    
def get_course_with_professor(cours_id):
    """Récupérer un cours spécifique avec son professeur"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.code, c.libelle, c.volume_horaire,
                       u.id as prof_id, u.nom as prof_nom, u.prenom as prof_prenom
                FROM cours c
                LEFT JOIN utilisateur u ON c.professeur_id = u.id
                WHERE c.id = %s
            """, [cours_id])
            
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "code": row[1],
                    "libelle": row[2],
                    "volumeHoraire": row[3],
                    "professeur_id": row[4],
                    "professeur_nom": f"{row[5]} {row[6]}" if row[5] and row[6] else "Non assigné"
                }
            return None
    except Exception as e:
        print(f"[DEBUG] Erreur récupération cours {cours_id}: {e}")
        return None
@auth_required_django(roles=["ADMINISTRATEUR"])
def seance_edit(request, seance_id):
    
    """Formulaire de modification de séance avec professeur - COMPLÈTE"""
    try:
        # Récupérer les informations de la séance
        seance_info = PLANNING_RPC.call("seance.get", {"id": seance_id})
        
        if not seance_info:
            messages.error(request, f"Séance ID {seance_id} non trouvée")
            return redirect('administration:planning_week')
        
        # DEBUG: Afficher les informations brutes
        print(f"\n[DEBUG seance_edit] Informations brutes de la séance:")
        for key, value in seance_info.items():
            print(f"  {key}: {value}")
        
        # Normaliser les IDs
        cours_id = None
        groupe_id = None
        
        # Extraire l'ID du cours
        for field in ['cours_id', 'cours', 'course_id', 'course']:
            if field in seance_info and seance_info[field]:
                try:
                    cours_id = int(seance_info[field])
                    print(f"[DEBUG] Cours ID trouvé dans '{field}': {cours_id}")
                    break
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] Erreur conversion cours {field}: {e}")
                    continue
        
        # Extraire l'ID du groupe
        for field in ['groupe_id', 'groupe', 'group_id', 'group']:
            if field in seance_info and seance_info[field]:
                try:
                    groupe_id = int(seance_info[field])
                    print(f"[DEBUG] Groupe ID trouvé dans '{field}': {groupe_id}")
                    break
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] Erreur conversion groupe {field}: {e}")
                    continue
        
        # Récupérer le cours avec son professeur
        professeur_actuel_id = None
        professeur_actuel_nom = "Non assigné"
        
        if cours_id:
            cours_details = get_course_with_professor(cours_id)
            if cours_details:
                professeur_actuel_id = cours_details.get('professeur_id')
                professeur_actuel_nom = cours_details.get('professeur_nom', 'Non assigné')
                print(f"[DEBUG] Professeur actuel: ID={professeur_actuel_id}, Nom={professeur_actuel_nom}")
        
        # Déterminer la semaine et l'année
        try:
            date_str = seance_info.get('date', '')
            if date_str:
                if isinstance(date_str, str):
                    seance_date = date.fromisoformat(date_str)
                elif hasattr(date_str, 'date'):
                    seance_date = date_str
                else:
                    seance_date = date.today()
                
                week = seance_date.isocalendar()[1]
                year = seance_date.isocalendar()[0]
                print(f"[DEBUG] Date séance: {date_str} -> Semaine {week}/{year}")
            else:
                week = int(request.GET.get('week', 1))
                year = int(request.GET.get('year', date.today().year))
        except Exception as e:
            print(f"[DEBUG] Erreur détermination semaine: {e}")
            week = int(request.GET.get('week', 1))
            year = int(request.GET.get('year', date.today().year))
        
        # Récupérer les listes pour les selects
        cours_list = get_courses_with_professors()
        professeurs = get_professeurs()
        groupes = get_groupes_with_promotions()
        filieres = get_filieres()
        promotions = get_promotions()
        
        # Initialiser les données du formulaire
        form_data = {
            'date': seance_info.get('date', ''),
            'heure_debut': seance_info.get('heure_debut', seance_info.get('heureDebut', '')),
            'heure_fin': seance_info.get('heure_fin', seance_info.get('heureFin', '')),
            'salle': seance_info.get('salle', ''),
            'cours_id': str(cours_id) if cours_id else '',
            'groupe_id': str(groupe_id) if groupe_id else '',
            'professeur_id': str(professeur_actuel_id) if professeur_actuel_id else '',
            'filiere_id': '',
            'promotion_id': ''
        }
        
        print(f"\n[DEBUG] Données formulaire initialisées:")
        for key, value in form_data.items():
            print(f"  {key}: {value}")
        
        # PARTIE POST - TRAITEMENT DE LA SOUMISSION
        if request.method == 'POST':
            print(f"\n[DEBUG] POST data reçu pour séance {seance_id}:")
            for key, value in request.POST.items():
                print(f"  {key}: {value}")
            
            try:
                # Récupération des données du formulaire
                date_val = request.POST.get('date', '').strip()
                heure_debut = request.POST.get('heure_debut', '').strip()
                heure_fin = request.POST.get('heure_fin', '').strip()
                salle = request.POST.get('salle', '').strip()
                cours_raw = request.POST.get('cours_id', '').strip()
                groupe_raw = request.POST.get('groupe_id', '').strip()
                professeur_raw = request.POST.get('professeur_id', '').strip()
                
                print(f"[DEBUG] Données extraites:")
                print(f"  Cours: {cours_raw}")
                print(f"  Professeur: {professeur_raw}")
                print(f"  Groupe: {groupe_raw}")
                
                # Validation des champs obligatoires
                errors = []
                
                if not date_val:
                    errors.append("La date est obligatoire")
                
                if not heure_debut:
                    errors.append("L'heure de début est obligatoire")
                
                if not heure_fin:
                    errors.append("L'heure de fin est obligatoire")
                
                if not salle:
                    errors.append("La salle est obligatoire")
                
                if not cours_raw:
                    errors.append("Le cours est obligatoire")
                
                if not groupe_raw:
                    errors.append("Le groupe est obligatoire")
                
                if errors:
                    raise ValueError(" | ".join(errors))
                
                # Conversion des IDs
                try:
                    cours_id_post = int(cours_raw)
                except (ValueError, TypeError):
                    raise ValueError("Veuillez sélectionner un cours valide")
                
                try:
                    groupe_id_post = int(groupe_raw)
                except (ValueError, TypeError):
                    raise ValueError("Veuillez sélectionner un groupe valide")
                
                # IMPORTANT: Gestion du professeur - SOLUTION COMPLÈTE
                professeur_id_updated = None
                if professeur_raw:
                    try:
                        professeur_id_updated = int(professeur_raw)
                        print(f"[DEBUG] Professeur sélectionné: ID {professeur_id_updated}")
                        
                        # Vérifier si le professeur a changé
                        if professeur_id_updated != professeur_actuel_id:
                            print(f"[DEBUG] Changement de professeur détecté: {professeur_actuel_id} -> {professeur_id_updated}")
                            
                            # OPTION 1: Mettre à jour via RPC
                            try:
                                print(f"[DEBUG] Tentative mise à jour via RPC...")
                                result = COURSE_RPC.call("course.update", {
                                    "id": cours_id_post,
                                    "professorId": professeur_id_updated
                                })
                                print(f"[DEBUG] RPC réussi: {result}")
                            except RpcError as e:
                                print(f"[DEBUG] Erreur RPC: {str(e)}")
                                
                                # OPTION 2: Mettre à jour directement en base si RPC échoue
                                print(f"[DEBUG] Tentative mise à jour directe en base...")
                                success = update_course_professor_direct(cours_id_post, professeur_id_updated)
                                if success:
                                    print(f"[DEBUG] Mise à jour directe réussie")
                                else:
                                    print(f"[DEBUG] Échec mise à jour directe")
                                    # Ne pas lever d'exception, continuer avec la séance
                    except (ValueError, TypeError) as e:
                        print(f"[DEBUG] Erreur conversion ID professeur: {e}")
                        # Pas d'erreur, le professeur n'est pas obligatoire
                else:
                    print(f"[DEBUG] Aucun professeur sélectionné")
                    # Si on veut retirer le professeur existant
                    if professeur_actuel_id:
                        print(f"[DEBUG] Retrait du professeur existant")
                        try:
                            COURSE_RPC.call("course.update", {
                                "id": cours_id_post,
                                "professorId": None
                            })
                        except:
                            update_course_professor_direct(cours_id_post, None)
                
                # Mettre à jour la séance
                params = {
                    "id": seance_id,
                    "date": date_val,
                    "heure_debut": heure_debut,
                    "heure_fin": heure_fin,
                    "salle": salle,
                    "cours": cours_id_post,
                    "groupe": groupe_id_post
                }
                
                print(f"[DEBUG] Paramètres pour mise à jour séance: {params}")
                
                # Mise à jour de la séance via RPC
                try:
                    result = PLANNING_RPC.call("seance.update", params)
                    print(f"[DEBUG] Séance mise à jour avec succès: {result}")
                except RpcError as e:
                    print(f"[DEBUG] Erreur RPC séance.update: {e}")
                    # Option de secours: mise à jour directe
                    update_seance_direct(seance_id, params)
                
                # Récupérer le nom du professeur pour le message
                professeur_nom = "Non assigné"
                if professeur_id_updated:
                    for prof in professeurs:
                        if prof['id'] == professeur_id_updated:
                            professeur_nom = prof['nom_complet']
                            break
                elif professeur_actuel_id:
                    professeur_nom = professeur_actuel_nom
                
                messages.success(request, f"✅ Séance modifiée avec succès. Professeur: {professeur_nom}")
                
                # Redirection avec timestamp pour éviter le cache
                redirect_url = f'/administration/planning/week/?week={week}&year={year}&refresh={int(time.time())}'
                print(f"[DEBUG] Redirection vers: {redirect_url}")
                return redirect(redirect_url)
                
            except RpcError as e:
                error_msg = f"Erreur serveur RPC: {str(e)}"
                print(f"[DEBUG] Erreur RPC: {error_msg}")
            except ValueError as e:
                error_msg = str(e)
                print(f"[DEBUG] Erreur validation: {error_msg}")
            except Exception as e:
                error_msg = f"Erreur inattendue: {str(e)}"
                print(f"[DEBUG] Erreur inattendue: {error_msg}")
                import traceback
                traceback.print_exc()
            
            # En cas d'erreur, garder les données soumises
            form_data = {
                'date': request.POST.get('date', form_data['date']),
                'heure_debut': request.POST.get('heure_debut', form_data['heure_debut']),
                'heure_fin': request.POST.get('heure_fin', form_data['heure_fin']),
                'salle': request.POST.get('salle', form_data['salle']),
                'cours_id': request.POST.get('cours_id', form_data['cours_id']),
                'groupe_id': request.POST.get('groupe_id', form_data['groupe_id']),
                'professeur_id': request.POST.get('professeur_id', form_data['professeur_id']),
                'filiere_id': request.POST.get('filiere_id', form_data['filiere_id']),
                'promotion_id': request.POST.get('promotion_id', form_data['promotion_id'])
            }
            
            print(f"[DEBUG] Form data après erreur: {form_data}")
            
            return render(request, 'administration/seance_edit.html', {
                'seance': seance_info,
                'error': error_msg,
                'cours_list': cours_list,
                'professeurs': professeurs,
                'groupes': groupes,
                'filieres': filieres,
                'promotions': promotions,
                'week': week,
                'year': year,
                'form_data': form_data,
                'professeur_actuel_id': professeur_actuel_id,
                'professeur_actuel_nom': professeur_actuel_nom
            })
        
        # PARTIE GET - AFFICHAGE DU FORMULAIRE
        print(f"\n[DEBUG] Affichage formulaire GET pour séance {seance_id}")
        print(f"  Cours ID dans form_data: {form_data['cours_id']}")
        print(f"  Groupe ID dans form_data: {form_data['groupe_id']}")
        print(f"  Professeur ID dans form_data: {form_data['professeur_id']}")
        
        return render(request, 'administration/seance_edit.html', {
            'seance': seance_info,
            'cours_list': cours_list,
            'professeurs': professeurs,
            'groupes': groupes,
            'filieres': filieres,
            'promotions': promotions,
            'week': week,
            'year': year,
            'form_data': form_data,
            'professeur_actuel_id': professeur_actuel_id,
            'professeur_actuel_nom': professeur_actuel_nom
        })
        
    except RpcError as e:
        messages.error(request, f"Erreur RPC: {str(e)}")
        print(f"[DEBUG] Erreur RPC dans seance_edit: {e}")
        return redirect('administration:planning_week')
    except Exception as e:
        messages.error(request, f"Erreur inattendue: {str(e)}")
        print(f"[DEBUG] Erreur inattendue dans seance_edit: {e}")
        import traceback
        traceback.print_exc()
        return redirect('administration:planning_week')


# AJOUTEZ CES FONCTIONS UTILITAIRES :

def update_seance_direct(seance_id, params):
    """Mettre à jour une séance directement en base"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                UPDATE seance 
                SET date = %s, 
                    heure_debut = %s, 
                    heure_fin = %s, 
                    salle = %s, 
                    cours_id = %s, 
                    groupe_id = %s
                WHERE id = %s
            """, [
                params['date'],
                params['heure_debut'],
                params['heure_fin'],
                params['salle'],
                params['cours'],
                params['groupe'],
                seance_id
            ])
            
            print(f"[DEBUG] Séance {seance_id} mise à jour directement")
            return True
    except Exception as e:
        print(f"[ERROR] Erreur mise à jour directe séance: {e}")
        return False

def get_course_with_professor(cours_id):
    """Récupérer un cours spécifique avec son professeur"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.code, c.libelle, c.volume_horaire,
                       u.id as prof_id, u.nom as prof_nom, u.prenom as prof_prenom
                FROM cours c
                LEFT JOIN utilisateur u ON c.professeur_id = u.id
                WHERE c.id = %s
            """, [cours_id])
            
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "code": row[1],
                    "libelle": row[2],
                    "volumeHoraire": row[3],
                    "professeur_id": row[4],
                    "professeur_nom": f"{row[5]} {row[6]}" if row[5] and row[6] else "Non assigné"
                }
            return None
    except Exception as e:
        print(f"[DEBUG] Erreur récupération cours {cours_id}: {e}")
        return None
def update_course_professor_direct(cours_id, professeur_id):
    """Mettre à jour le professeur d'un cours directement en base"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            if professeur_id:
                cur.execute("""
                    UPDATE cours 
                    SET professeur_id = %s 
                    WHERE id = %s
                """, [professeur_id, cours_id])
            else:
                cur.execute("""
                    UPDATE cours 
                    SET professeur_id = NULL 
                    WHERE id = %s
                """, [cours_id])
            
            return True
    except Exception as e:
        print(f"[ERROR] Erreur mise à jour directe cours: {e}")
        return False    
@auth_required_django(roles=["ADMINISTRATEUR"])
def seance_delete(request, seance_id):
    """Suppression d'une séance"""
    if request.method == 'POST':
        try:
            result = PLANNING_RPC.call("seance.delete", {"id": seance_id})
            messages.success(request, "Séance supprimée avec succès")
            return redirect('administration:planning_week')
                
        except RpcError as e:
            messages.error(request, f"Erreur: {str(e)}")
        except Exception as e:
            messages.error(request, f"Erreur inattendue: {str(e)}")
        
        return redirect('administration:planning_week')
    
    try:
        seance_info = PLANNING_RPC.call("seance.get", {"id": seance_id})
        if not seance_info:
            messages.error(request, "Séance non trouvée")
            return redirect('administration:planning_week')
            
        return render(request, 'administration/seance_delete.html', {
            'seance': seance_info
        })
    except RpcError as e:
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('administration:planning_week')

# ==========================
# Utilitaires
# ==========================
# administration/views.py - MODIFIEZ CETTE FONCTION
def get_course_with_professor(cours_id):
    """Récupérer un cours spécifique avec les informations de son professeur"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id,
                    c.code,
                    c.libelle,
                    c.volume_horaire,
                    c.professeur_id,
                    u.nom as prof_nom,
                    u.prenom as prof_prenom,
                    u.email as prof_email
                FROM cours c
                LEFT JOIN utilisateur u ON c.professeur_id = u.id
                WHERE c.id = %s
            """, [cours_id])
            
            row = cur.fetchone()
            if row:
                cours = {
                    "id": row[0],
                    "code": row[1] or "",
                    "libelle": row[2] or "",
                    "volumeHoraire": row[3] or 0,
                    "professeur_id": row[4],
                }
                
                # Construire le nom du professeur
                if row[5] and row[6]:
                    cours["professeur_nom"] = f"{row[5]} {row[6]}"
                elif row[5]:
                    cours["professeur_nom"] = row[5]
                elif row[6]:
                    cours["professeur_nom"] = row[6]
                else:
                    cours["professeur_nom"] = "Non assigné"
                
                print(f"[DEBUG get_course_with_professor] Cours trouvé: {cours}")
                return cours
        
        print(f"[DEBUG get_course_with_professor] Cours {cours_id} non trouvé")
        return None
    except Exception as e:
        print(f"[ERROR get_course_with_professor] Erreur: {e}")
        return None
def get_courses():
    """Récupérer la liste des cours"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT id, code, libelle, volume_horaire 
                FROM cours 
                ORDER BY code
            """)
            rows = cur.fetchall()
            
            return [
                {
                    "id": r[0],
                    "code": r[1],
                    "libelle": r[2],
                    "volumeHoraire": r[3]
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[DEBUG] Erreur récupération cours: {e}")
        return []
@auth_required_django(roles=["ADMINISTRATEUR"])
def get_default_group(request):
    """Trouver un groupe par défaut pour une promotion"""
    promotion_id = request.GET.get('promotion_id')
    
    if not promotion_id:
        return JsonResponse({'error': 'Promotion ID manquant'})
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT id, nom 
                FROM groupe 
                WHERE promotion_id = %s 
                ORDER BY nom 
                LIMIT 1
            """, [promotion_id])
            
            result = cur.fetchone()
            
            if result:
                return JsonResponse({
                    'group_id': result[0],
                    'group_name': result[1],
                    'success': True
                })
            else:
                # Si aucun groupe n'existe, en créer un par défaut
                cur.execute("""
                    INSERT INTO groupe (nom, promotion_id)
                    VALUES (%s, %s)
                    RETURNING id
                """, [f"Groupe Principal - Promotion {promotion_id}", promotion_id])
                
                new_group_id = cur.fetchone()[0]
                
                return JsonResponse({
                    'group_id': new_group_id,
                    'group_name': f"Groupe Principal - Promotion {promotion_id}",
                    'success': True,
                    'created': True
                })
                
    except Exception as e:
        return JsonResponse({'error': str(e)})

@auth_required_django(roles=["ADMINISTRATEUR"])
def planning_generate(request: HttpRequest):
    error = None
    success = None

    if request.method == "POST":
        try:
            week = int(request.POST.get("week", "1") or 1)
            year = int(request.POST.get("year", str(dt_date.today().year)) or dt_date.today().year)
            result = PLANNING_RPC.call("planning.generate", {"week": week, "year": year, "administrateurId": 1})
            success = f"Planning généré: {result}"
        except Exception as e:
            error = str(e)

    return render(request, "administration/planning_generate.html", {"error": error, "success": success})

def get_user_info(request):
    """Récupérer les informations de l'utilisateur pour le contexte"""
    user_id = request.session.get('user_id')
    if user_id:
        return {
            'user_id': user_id,
            'user_nom': request.session.get('user_nom', 'Admin'),
            'user_prenom': request.session.get('user_prenom', 'Système'),
            'user_email': request.session.get('user_email', ''),
            'user_type': request.session.get('user_type', 'ADMINISTRATEUR')
        }
    return {}
def get_professeurs():
    """Récupérer la liste des professeurs avec noms"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.nom, u.prenom, u.email, u.type_utilisateur
                FROM utilisateur u
                WHERE u.type_utilisateur = 'PROFESSEUR' OR u.type_utilisateur = 'ENSEIGNANT'
                ORDER BY u.nom, u.prenom
            """)
            rows = cur.fetchall()
            
            professeurs = []
            for r in rows:
                professeur = {
                    "id": r[0] or 0,
                    "nom": r[1] or "",
                    "prenom": r[2] or "",
                    "email": r[3] or "",
                    "type": r[4] or "",
                    "nom_complet": f"{r[1] or ''} {r[2] or ''}".strip()
                }
                professeurs.append(professeur)
            
            return professeurs
    except Exception as e:
        print(f"[ERROR] Erreur récupération professeurs: {e}")
        return []
def get_professeur_by_cours_id(cours_id):
    """Récupérer le professeur assigné à un cours"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.nom, u.prenom, u.email
                FROM cours c
                LEFT JOIN utilisateur u ON c.professeur_id = u.id
                WHERE c.id = %s
                LIMIT 1
            """, [cours_id])
            
            row = cur.fetchone()
            if row and row[0]:
                return {
                    "id": row[0],
                    "nom": row[1],
                    "prenom": row[2],
                    "email": row[3],
                    "nom_complet": f"{row[1]} {row[2]}"
                }
            return None
    except Exception as e:
        print(f"[ERROR] Erreur récupération professeur pour cours {cours_id}: {e}")
        return None
def get_filieres():
    """Récupérer la liste des filières"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT id, code, nom, niveau
                FROM filiere 
                ORDER BY code
            """)
            rows = cur.fetchall()
            
            return [
                {
                    "id": r[0],
                    "code": r[1],
                    "nom": r[2],
                    "description": r[3]  # mapped from 'niveau'
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[DEBUG] Erreur récupération filières: {e}")
        return []

def get_promotions():
    """Récupérer la liste des promotions"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.annee_scolaire, p.libelle, p.filiere_id, f.nom as filiere_nom
                FROM promotion p
                LEFT JOIN filiere f ON p.filiere_id = f.id
                ORDER BY p.annee_scolaire DESC, p.libelle
            """)
            rows = cur.fetchall()

            # debug: log number of promotions and sample
            try:
                print(f"[DEBUG] Promotions count: {len(rows)}; sample: {rows[:3]}")
            except Exception:
                pass
            
            return [
                {
                    "id": r[0],
                    "annee": r[1],  # from annee_scolaire
                    "libelle": r[2],
                    "filiere_id": (r[3] if r[3] is not None else ''),  # ensure '' when NULL for template data-* attributes
                    "filiere_nom": r[4],
                    "nom_complet": f"{r[2]} - {r[1]} ({r[4]})"
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[DEBUG] Erreur récupération promotions: {e}")
        return []


def get_course_with_professor(cours_id):
    """Récupérer un cours spécifique avec son professeur"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.code, c.libelle, c.volume_horaire,
                       u.id as prof_id, u.nom as prof_nom, u.prenom as prof_prenom
                FROM cours c
                LEFT JOIN utilisateur u ON c.professeur_id = u.id
                WHERE c.id = %s
            """, [cours_id])
            
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "code": row[1],
                    "libelle": row[2],
                    "volumeHoraire": row[3],
                    "professeur_id": row[4],
                    "professeur_nom": f"{row[5]} {row[6]}" if row[5] and row[6] else "Non assigné"
                }
            return None
    except Exception as e:
        print(f"[DEBUG] Erreur récupération cours {cours_id}: {e}")
        return None

def get_groupes_with_promotions():
    """Récupérer la liste des groupes avec promotions"""
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT g.id, g.nom, p.id as promotion_id, p.libelle as promotion_libelle,
                       p.annee_scolaire, f.nom as filiere_nom
                FROM groupe g
                LEFT JOIN promotion p ON g.promotion_id = p.id
                LEFT JOIN filiere f ON p.filiere_id = f.id
                ORDER BY p.annee_scolaire DESC, g.nom
            """)
            rows = cur.fetchall()
            
            return [
                {
                    "id": r[0],
                    "nom": r[1],
                    "promotion_id": r[2],
                    "promotion_libelle": r[3],
                    "annee": r[4],
                    "filiere_nom": r[5],
                    "nom_complet": f"{r[1]} - {r[3]} {r[4]} ({r[5]})"
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[DEBUG] Erreur récupération groupes avec promotions: {e}")
        return []


@auth_required_django(roles=["ADMINISTRATEUR"])
def get_default_group(request: HttpRequest):
    """Retourne un groupe par défaut (JSON) pour une promotion donnée"""
    promotion_id = request.GET.get('promotion_id')
    if not promotion_id:
        return JsonResponse({}, status=200)

    try:
        pid = int(promotion_id)
    except (ValueError, TypeError):
        return JsonResponse({}, status=200)

    from django.db import connection
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT id FROM groupe WHERE promotion_id = %s LIMIT 1
            """, (pid,))
            row = cur.fetchone()
            if row:
                return JsonResponse({'group_id': row[0]})
            else:
                return JsonResponse({}, status=200)
    except Exception as e:
        print(f"[DEBUG] Erreur get_default_group: {e}")
        return JsonResponse({}, status=200)