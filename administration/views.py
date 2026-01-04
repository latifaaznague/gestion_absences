from datetime import date as dt_date
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpRequest, HttpResponseForbidden
from services.rpc_client import RpcError, JsonRpcClient
from services.db import get_conn
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
    if "rpc_token" not in request.session:
        return redirect("accounts:login")
    
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
    stats = dashboard_stats()
    return render(request, 'administration/dashboard.html', {'stats': stats})

# ==========================
# Courses
# ==========================

@auth_required_django(roles=["ADMINISTRATEUR"])
def cours_list(request: HttpRequest):
    error = None
    courses = []
    try:
        courses = COURSE_RPC.call("course.list", {})
    except RpcError as e:
        error = str(e)
    return render(request, "administration/cours_list.html", {"courses": courses, "error": error})

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
            return render(request, "administration/cours_form.html", {
                "mode": "create",
                "error": error,
                "course": payload,
                "profs": profs
            })

    return render(request, "administration/cours_form.html", {
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
    except Exception:
        profs = []

    courses = COURSE_RPC.call("course.list", {})
    course = next((x for x in courses if int(x["id"]) == pk), None)
    if not course:
        return redirect("administration:cours_list")

    try:
        if course.get("professorId") is not None:
            course["professorId"] = int(course["professorId"])
    except Exception:
        course["professorId"] = None

    if request.method == "POST":
        prof_id_raw = request.POST.get("professorId") or ""
        prof_id = int(prof_id_raw) if prof_id_raw else None

        payload = {
            "id": pk,
            "code": request.POST.get("code", "").strip(),
            "libelle": request.POST.get("libelle", "").strip(),
            "volumeHoraire": int(request.POST.get("volumeHoraire", "0") or 0),
            "professorId": prof_id,
        }

        try:
            COURSE_RPC.call("course.update", payload)
            return redirect("administration:cours_list")
        except Exception as e:
            return render(request, "administration/cours_form.html", {
                "mode": "edit",
                "error": str(e),
                "course": payload,
                "profs": profs
            })

    return render(request, "administration/cours_form.html", {
        "mode": "edit",
        "error": None,
        "course": course,
        "profs": profs
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
            STUDENT_RPC.call("student.create", {
                "nom": request.POST.get("nom", "").strip(),
                "prenom": request.POST.get("prenom", "").strip(),
                "email": request.POST.get("email", "").strip(),
                "promotionId": int(request.POST.get("promotionId", 0)),
                "codeEtudiant": request.POST.get("codeEtudiant", "").strip(),
                "motDePasse": request.POST.get("motDePasse", "").strip(),
            })
            return redirect("administration:student_list")
        except Exception as e:
            error = str(e)

    return render(request, "administration/student_form.html", {
        "mode": "create",
        "error": error,
        "student": {"nom": "", "prenom": "", "email": "", "promotionId": "", "codeEtudiant": "", "motDePasse": ""},
        "filieres": filieres,
        "promotions": promotions,
    })

@auth_required_django(roles=["ADMINISTRATEUR"])
def student_edit(request: HttpRequest, student_id: int):
    error = None
    student = None

    try:
        students = STUDENT_RPC.call("student.list", {})
        student = next((s for s in students if s["id"] == student_id), None)
        if not student:
            error = "Étudiant introuvable"
        filieres = STUDENT_RPC.call("filiere.list")
        promotions = STUDENT_RPC.call("promotion.list")
    except Exception as e:
        error = str(e)
        filieres = promotions = []

    if request.method == "POST":
        try:
            payload = {
                "id": student_id,
                "nom": request.POST.get("nom", "").strip(),
                "prenom": request.POST.get("prenom", "").strip(),
                "email": request.POST.get("email", "").strip(),
                "promotionId": int(request.POST.get("promotionId", "0")),
                "codeEtudiant": request.POST.get("codeEtudiant", "").strip(),
            }
            mp = request.POST.get("motDePasse", "").strip()
            if mp:
                payload["motDePasse"] = mp

            STUDENT_RPC.call("student.update", payload)
            return redirect("administration:student_list")
        except Exception as e:
            error = str(e)

    return render(request, "administration/student_form.html", {
        "mode": "edit",
        "error": error,
        "student": student,
        "filieres": filieres,
        "promotions": promotions,
    })

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

@auth_required_django(roles=["ADMINISTRATEUR"])
def planning_week(request):
    """Planning semaine - version simple"""
    week = int(request.GET.get('week', 1))
    year = int(request.GET.get('year', 2025))
    
    try:
        sessions = PLANNING_RPC.call("planning.getWeek", {"week": week, "year": year})
    except RpcError as e:
        sessions = []
        print(f"[DEBUG] Vue: Erreur RPC: {e}")
    
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    
    week_dates = []
    for i in range(7):
        day_date = monday + timedelta(days=i)
        week_dates.append({
            'date': day_date,
            'name': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][i],
            'date_iso': day_date.isoformat()
        })
    
    sessions_by_day = {}
    for session in sessions:
        day = session.get('date')
        if day:
            if day not in sessions_by_day:
                sessions_by_day[day] = []
            sessions_by_day[day].append(session)
    
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
    
    context = {
        'week': week,
        'year': year,
        'days_with_sessions': days_with_sessions,
        'monday': monday,
        'sunday': sunday,
    }
    
    return render(request, 'administration/planning_week.html', context)

# ==========================
# Séances
# ==========================

@auth_required_django(roles=["ADMINISTRATEUR"])
def seance_add(request):
    """Formulaire d'ajout de séance"""
    week = int(request.GET.get('week', 1))
    year = int(request.GET.get('year', 2025))
    prefilled_date = request.GET.get('date', '')
    
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    
    if request.method == 'POST':
        try:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT id FROM planning 
                    WHERE semaine = %s AND annee = %s
                    LIMIT 1
                """, (week, year))
                
                row = cur.fetchone()
                
                if row:
                    planning_id = row[0]
                else:
                    cur.execute("""
                        INSERT INTO planning(semaine, annee, administrateur_id, date_creation)
                        VALUES (%s, %s, %s, NOW()) 
                        RETURNING id
                    """, (week, year, 1))
                    planning_id = cur.fetchone()[0]
            
            params = {
                "date": request.POST.get('date'),
                "heure_debut": request.POST.get('heure_debut'),
                "heure_fin": request.POST.get('heure_fin'),
                "salle": request.POST.get('salle'),
                "cours": int(request.POST.get('cours_id')),
                "groupe": int(request.POST.get('groupe_id')),
                "planning_id": planning_id
            }
            
            result = PLANNING_RPC.call("seance.add", params)
            
            messages.success(request, f"Séance ajoutée avec succès (ID: {result.get('id')})")
            return redirect(f'/administration/planning/week/?week={week}&year={year}')
            
        except RpcError as e:
            error_msg = f"Erreur RPC: {str(e)}"
        except ValueError as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f"Erreur inattendue: {str(e)}"
        
        return render(request, 'administration/seance_add.html', {
            'week': week,
            'year': year,
            'monday': monday,
            'sunday': sunday,
            'prefilled_date': request.POST.get('date'),
            'error': error_msg,
            'cours_list': get_courses(),
            'groupes': get_groupes(),
            'form_data': request.POST
        })
    
    return render(request, 'administration/seance_add.html', {
        'week': week,
        'year': year,
        'monday': monday,
        'sunday': sunday,
        'prefilled_date': prefilled_date,
        'cours_list': get_courses(),
        'groupes': get_groupes(),
    })

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

@auth_required_django(roles=["ADMINISTRATEUR"])
def seance_edit(request, seance_id):
    """Formulaire de modification de séance"""
    try:
        seance_info = PLANNING_RPC.call("seance.get", {"id": seance_id})
        
        if not seance_info:
            messages.error(request, f"Séance ID {seance_id} non trouvée")
            return redirect('administration:planning_week')
        
        seance_date = date.fromisoformat(seance_info.get('date'))
        week = seance_date.isocalendar()[1]
        year = seance_date.isocalendar()[0]
        
        if request.method == 'POST':
            try:
                params = {
                    "id": seance_id,
                    "date": request.POST.get('date'),
                    "heure_debut": request.POST.get('heure_debut'),
                    "heure_fin": request.POST.get('heure_fin'),
                    "salle": request.POST.get('salle'),
                    "cours": int(request.POST.get('cours_id')),
                    "groupe": int(request.POST.get('groupe_id'))
                }
                
                result = PLANNING_RPC.call("seance.update", params)
                messages.success(request, "Séance modifiée avec succès")
                return redirect(f'/administration/planning/week/?week={week}&year={year}')
                
            except RpcError as e:
                error_msg = f"Erreur RPC: {str(e)}"
            except ValueError as e:
                error_msg = str(e)
            except Exception as e:
                error_msg = f"Erreur inattendue: {str(e)}"
            
            return render(request, 'administration/seance_edit.html', {
                'seance': seance_info,
                'error': error_msg,
                'cours_list': get_courses(),
                'groupes': get_groupes(),
                'week': week,
                'year': year
            })
        
        return render(request, 'administration/seance_edit.html', {
            'seance': seance_info,
            'cours_list': get_courses(),
            'groupes': get_groupes(),
            'week': week,
            'year': year
        })
        
    except RpcError as e:
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('administration:planning_week')

# ==========================
# Utilitaires
# ==========================

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

def get_groupes():
    from django.db import connection
    
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT id, nom, promotion_id 
                FROM groupe 
                ORDER BY nom
            """)
            rows = cur.fetchall()
            
            return [
                {
                    "id": r[0],
                    "nom": r[1],
                    "promotionId": r[2]
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[DEBUG] Erreur récupération groupes: {e}")
        return []

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