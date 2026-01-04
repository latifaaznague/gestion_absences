# professeurs/views.py - VERSION CORRIGÉE
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.utils import timezone
from datetime import datetime, timedelta
import json
import base64
import os
from django.conf import settings
from django.db.models import Count, Q, Max
from Home.models import Utilisateur, Professeur, Cours, Seance, Presence, Etudiant, Groupe, EtudiantGroupe


# Remplacer la fonction existante par :
def get_professeur_from_user_id(user_id):
    """
    Récupère le professeur à partir de user_id
    """
    try:
        # CORRECTION : Utiliser get_object_or_404 avec la relation correcte
        return Professeur.objects.get(utilisateur_id=user_id)
    except Professeur.DoesNotExist:
        return None
# Helper utilities for files
def detecter_type_fichier(blob):
    """Détecte le type MIME d'un fichier à partir de ses octets (heuristique simple)."""
    try:
        if blob is None:
            return 'application/octet-stream'
        # normalize to bytes
        if hasattr(blob, 'tobytes'):
            data = blob.tobytes()
        elif isinstance(blob, bytes):
            data = blob
        elif isinstance(blob, memoryview):
            data = blob.tobytes()
        else:
            data = bytes(blob)

        if data.startswith(b'%PDF'):
            return 'application/pdf'
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return 'image/png'
        if data[:2] == b'\xff\xd8':
            return 'image/jpeg'
        # Office Open XML (docx) and others are zip-based
        if data[:2] == b'PK':
            # We can't reliably distinguish zip types here, return generic
            return 'application/zip'
        # Fallback: try using Python's mimetypes based on a heuristic extension (none) -> octet-stream
        return 'application/octet-stream'
    except Exception:
        return 'application/octet-stream'

# Normalisation et détection avancée des bytes stockés
def normalize_file_bytes(value):
    """Normalise la valeur stockée dans le champ (bytes/memoryview/base64 string) et
    retourne un tuple (bytes_data, was_base64) où was_base64 indique si on a décodé du base64."""
    try:
        if value is None:
            return (None, False)
        # obtenir raw bytes
        if hasattr(value, 'tobytes'):
            data = value.tobytes()
        elif isinstance(value, bytes):
            data = value
        elif isinstance(value, memoryview):
            data = value.tobytes()
        else:
            try:
                data = bytes(value)
            except Exception:
                data = None

        if not data:
            return (None, False)

        # Détection simple (headers connus)
        if data.startswith(b'%PDF') or data.startswith(b"\x89PNG\r\n\x1a\n") or data[:2] == b'\xff\xd8':
            return (data, False)

        # Si ce sont des caractères ascii plausibles base64, tenter un décodage base64 sécurisé
        try:
            s = data.strip()
            # uniquement si composé d'octets ascii
            if all(32 <= b <= 126 for b in s):
                decoded = base64.b64decode(s, validate=True)
                if decoded.startswith(b'%PDF') or decoded.startswith(b"\x89PNG\r\n\x1a\n") or decoded[:2] == b'\xff\xd8':
                    return (decoded, True)
        except Exception:
            pass

        # fallback: return data as-is
        return (data, False)
    except Exception:
        return (None, False)

# =========================================
# Fonctions utilitaires CORRIGÉES
# =========================================

def check_professor_auth(request):
    """
    Vérifie si l'utilisateur est un professeur connecté
    Retourne user_id si OK, None sinon
    """
    if not request.session.get('logged_in'):
        return None
    
    if request.session.get('user_role') != 'PROFESSEUR':
        return None
    
    return request.session.get('user_id')
# professeurs/views.py - CORRECTION DES VUES

def dashboard_professeur(request):
    """Affiche le tableau de bord du professeur - VERSION CORRIGÉE"""
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        # Récupérer le professeur avec la fonction corrigée
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            return redirect('/login/')
        
        utilisateur = prof.utilisateur
        
        today = datetime.now().date()
        
        # ================== CORRECTION DES STATISTIQUES ==================
        # Utiliser ORM au lieu de SQL raw pour plus de fiabilité
        
        # Séances aujourd'hui
        seances_aujourdhui = Seance.objects.filter(
            cours__professeur=prof,
            date=today
        ).select_related('cours', 'groupe').order_by('heure_debut')
        
        total_seances_aujourdhui = seances_aujourdhui.count()
        
        # Séances de la semaine
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        seances_semaine = Seance.objects.filter(
            cours__professeur=prof,
            date__range=[start_of_week, end_of_week]
        ).select_related('cours', 'groupe').order_by('date', 'heure_debut')
        
        # Nombre de cours
        total_cours = Cours.objects.filter(professeur=prof).count()
        
        # Justifications en attente
        justifications_attente = Presence.objects.filter(
            seance__cours__professeur=prof,
            statut='ABSENT_JUSTIFIE',
            statut_justification='EN_ATTENTE'
        ).select_related('etudiant__utilisateur', 'seance__cours')
        
        total_justifications_attente = justifications_attente.count()
        
        # ================== CALCUL DES STATISTIQUES AVEC ORM ==================
        # 1. Statistiques pour les 30 derniers jours
        date_30_jours = today - timedelta(days=30)
        
        presences_30_jours = Presence.objects.filter(
            seance__cours__professeur=prof,
            seance__date__gte=date_30_jours
        )
        
        total_presences_30 = presences_30_jours.count()
        presents_30 = presences_30_jours.filter(statut='PRESENT').count()
        absents_justifies_30 = presences_30_jours.filter(statut='ABSENT_JUSTIFIE').count()
        absents_non_justifies_30 = presences_30_jours.filter(statut='ABSENT_NON_JUSTIFIE').count()
        total_absences_30 = absents_justifies_30 + absents_non_justifies_30
        
        if total_presences_30 > 0:
            taux_presence_30 = round((presents_30 / total_presences_30) * 100, 2)
        else:
            taux_presence_30 = 0
        
        # 2. Statistiques globales (toutes les séances)
        presences_all = Presence.objects.filter(
            seance__cours__professeur=prof
        )
        
        total_presences_all = presences_all.count()
        presents_all = presences_all.filter(statut='PRESENT').count()
        absents_justifies_all = presences_all.filter(statut='ABSENT_JUSTIFIE').count()
        absents_non_justifies_all = presences_all.filter(statut='ABSENT_NON_JUSTIFIE').count()
        total_absences_all = absents_justifies_all + absents_non_justifies_all
        
        if total_presences_all > 0:
            taux_presence_all = round((presents_all / total_presences_all) * 100, 2)
        else:
            taux_presence_all = 0
        
        # ================== PRÉPARATION DU CONTEXTE ==================
        context = {
            'prof': prof,
            'utilisateur': utilisateur,
            'today': today,
            'start_of_week': start_of_week,
            'end_of_week': end_of_week,
            
            # Données principales
            'seances_aujourdhui': seances_aujourdhui,
            'seances_semaine': seances_semaine,
            'justifications_attente': justifications_attente[:5],  # 5 premières pour l'affichage
            'total_justifications_attente': total_justifications_attente,
            'total_cours': total_cours,
            'total_seances_aujourdhui': total_seances_aujourdhui,
            'total_seances_semaine': seances_semaine.count(),
            
            # Statistiques pour les 30 derniers jours (affichées dans le dashboard)
            'stats': {
                'period_label': '30 derniers jours',
                'total_seances': total_presences_30,  # Approximatif
                'total_presences': total_presences_30,
                'presents': presents_30,
                'absents_justifies': absents_justifies_30,
                'absents_non_justifies': absents_non_justifies_30,
                'total_absences': total_absences_30,
                'taux_presence': taux_presence_30,
            },
            
            # Statistiques globales (affichées dans le panneau de droite)
            'stats_all': {
                'period_label': 'Tous',
                'total_seances': total_presences_all,  # Approximatif
                'total_presences': total_presences_all,
                'presents': presents_all,
                'absents_justifies': absents_justifies_all,
                'absents_non_justifies': absents_non_justifies_all,
                'total_absences': total_absences_all,
                'taux_presence': taux_presence_all,
            },
        }
        
        # ================== DEBUG ==================
        print(f"DEBUG - Taux présence 30 jours: {taux_presence_30}%")
        print(f"DEBUG - Total présences 30 jours: {total_presences_30}")
        print(f"DEBUG - Total justifications en attente: {total_justifications_attente}")
        print(f"DEBUG - Séances aujourd'hui: {total_seances_aujourdhui}")
        
        return render(request, 'professeurs/dashboard.html', context)
        
    except Exception as e:
        print(f"ERREUR dashboard_professeur: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect('/login/')

# CORRIGEZ la fonction profil_professeur
def profil_professeur(request):
    """Profil du professeur - VERSION ORM"""
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        # Récupérer avec ORM
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            return redirect('/login/')

        utilisateur = prof.utilisateur

        # Calculs simples pour le template
        total_cours = Cours.objects.filter(professeur=prof).count()
        total_seances = Seance.objects.filter(cours__professeur=prof).count()
        derniers_cours = Cours.objects.filter(professeur=prof).order_by('-id')[:5]
        dernieres_seances = Seance.objects.filter(cours__professeur=prof).order_by('-date')[:5]

        context = {
            'prof': prof,
            'utilisateur': utilisateur,
            'professeur': {
                'id': user_id,
                'nom': utilisateur.nom,
                'prenom': utilisateur.prenom,
                'email': utilisateur.email,
                'date_creation': utilisateur.date_creation,
                'specialite': prof.specialite or 'Non spécifiée'
            },
            'total_cours': total_cours,
            'total_seances': total_seances,
            'derniers_cours': list(derniers_cours),
            'dernieres_seances': list(dernieres_seances),
            'today': timezone.now().date(),
        }

        return render(request, 'professeurs/profil.html', context)
        
    except Exception as e:
        print(f"Erreur profil professeur: {str(e)}")
        return redirect('/login/')

# CORRIGEZ la fonction modifier_profil
def modifier_profil(request):
    """Modifier le profil du professeur"""
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    if request.method == 'POST':
        try:
            nom = request.POST.get('nom')
            prenom = request.POST.get('prenom')
            email = request.POST.get('email')
            specialite = request.POST.get('specialite')
            
            # Utiliser ORM pour les mises à jour
            from django.db import transaction
            
            with transaction.atomic():
                # Mettre à jour utilisateur
                Utilisateur.objects.filter(id=user_id).update(
                    nom=nom,
                    prenom=prenom,
                    email=email
                )
                
                # Mettre à jour professeur
                Professeur.objects.filter(utilisateur_id=user_id).update(
                    specialite=specialite
                )
                
                # Mettre à jour la session
                request.session['user_nom'] = nom
                request.session['user_prenom'] = prenom
                request.session['user_email'] = email
                
                messages.success(request, "Profil mis à jour avec succès!")
                
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
        
        return redirect('professeurs:profil_professeur')

    # GET -> afficher le formulaire de modification
    try:
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')

        utilisateur = prof.utilisateur
        context = {
            'prof': prof,
            'utilisateur': utilisateur,
            'today': timezone.now().date(),
        }
        return render(request, 'professeurs/modifier_profil.html', context)
    except Exception as e:
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('professeurs:profil_professeur')
# =========================================
# Déconnexion
# =========================================

def logout_view(request):
    """Déconnexion depuis l'espace professeur: vider la session et rediriger vers la page de login"""
    try:
        print(f"[DEBUG] logout_view - Déconnexion, ancienne session: {dict(request.session)}")
    except Exception:
        pass
    request.session.flush()
    messages.success(request, "Déconnecté avec succès")
    return redirect('/login/')

# test_db_structure.py
from django.db import connection

def test_professeur_structure():
    print("=== STRUCTURE DE LA TABLE PROFESSEUR ===")
    
    with connection.cursor() as cursor:
        # Voir les colonnes de la table professeur
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'professeur'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("Colonnes de la table 'professeur':")
        for col in columns:
            print(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
        
        print("\n=== TEST DE REQUÊTE ===")
        cursor.execute("SELECT id, specialite FROM professeur LIMIT 1")
        row = cursor.fetchone()
        print(f"Premier professeur: {row}")
        
        print("\n=== TEST DE JOINTURE ===")
        cursor.execute("""
            SELECT p.id, u.nom, u.prenom 
            FROM professeur p
            JOIN utilisateur u ON p.id = u.id
            LIMIT 1
        """)
        row = cursor.fetchone()
        print(f"Professeur avec utilisateur: {row}")

if __name__ == "__main__":
    test_professeur_structure()




# =========================================
# Gestion des cours - CORRIGÉ
# =========================================

def mes_cours(request):
    """Liste des cours du professeur"""
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        # Utiliser ORM pour fournir les données attendues par le template
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')

        utilisateur = prof.utilisateur

        cours_qs = Cours.objects.filter(professeur=prof).order_by('libelle')
        cours_list = []
        for c in cours_qs:
            nb_seances = Seance.objects.filter(cours=c).count()
            groupes = list(Groupe.objects.filter(seances__cours=c).distinct().values_list('nom', flat=True))
            salles = list(Seance.objects.filter(cours=c).exclude(salle__isnull=True).exclude(salle__exact='').values_list('salle', flat=True).distinct())

            cours_list.append({
                'id': c.id,
                'code': getattr(c, 'code', ''),
                'libelle': getattr(c, 'libelle', ''),
                'volume_horaire': getattr(c, 'volume_horaire', 0),
                'statistiques': {
                    'nombre_seances': nb_seances,
                    'nombre_groupes': len(groupes)
                },
                'groupes': groupes,
                'salles': salles,
                'periode': getattr(c, 'periode', None),
                'description': getattr(c, 'description', '')
            })

        # AJOUTEZ CE CALCUL POUR LES JUSTIFICATIONS EN ATTENTE
        total_justifications_attente = Presence.objects.filter(
            seance__cours__professeur=prof,
            statut='ABSENT_JUSTIFIE',
            statut_justification='EN_ATTENTE'
        ).count()

        context = {
            'prof': prof,
            'utilisateur': utilisateur,
            'cours_professeur': cours_list,
            'total_cours': len(cours_list),
            'total_justifications_attente': total_justifications_attente,  # ← AJOUTEZ CETTE LIGNE
            'today': timezone.now().date(),  # ← Ajoutez aussi today pour le footer
        }
            
    except Exception as e:
        print(f"Erreur mes_cours: {str(e)}")
        context = {
            'cours_professeur': [], 
            'prof': None, 
            'utilisateur': None, 
            'total_cours': 0,
            'total_justifications_attente': 0,
            'today': timezone.now().date(),
        }
    
    return render(request, 'professeurs/mes_cours.html', context)

def detail_cours(request, cours_id):
    """Affiche les détails d'un cours spécifique"""
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        # Récupérer le professeur - CORRECTION ICI
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')
            
        today = timezone.now().date()
        
        # Récupérer le cours
        cours = get_object_or_404(Cours, id=cours_id, professeur=prof)
        
        # Récupérer les séances
        seances = Seance.objects.filter(cours=cours).order_by('-date', 'heure_debut')
        total_seances = seances.count()
        
        # Récupérer les présences
        presences = Presence.objects.filter(seance__cours=cours)
        total_presences = presences.count()
        
        # Calculer les statistiques
        presents = presences.filter(statut='PRESENT').count()
        absents_justifies = presences.filter(statut='ABSENT_JUSTIFIE').count()
        absents_non_justifies = presences.filter(statut='ABSENT_NON_JUSTIFIE').count()
        
        if total_presences > 0:
            taux_presence = round((presents / total_presences * 100), 2)
        else:
            taux_presence = 0
        
        # Calculer le nombre d'étudiants uniques
        etudiant_ids = presences.values_list('etudiant_id', flat=True).distinct().count()
        
        # Récupérer les prochaines séances
        prochaines_seances = seances.filter(date__gte=today).order_by('date', 'heure_debut')[:5]
        
        # Récupérer les séances passées
        seances_passees = seances.filter(date__lt=today).order_by('-date')[:5]
        
        # Préparer le contexte
        context = {
            "prof": prof,
            "utilisateur": prof.utilisateur,
            "cours": cours,
            "seances": seances,
            "total_seances": total_seances,
            "prochaines_seances": prochaines_seances,
            "seances_passees": seances_passees,
            "total_etudiants": etudiant_ids,
            "statistiques": {
                "total_presences": total_presences,
                "presents": presents,
                "absents_justifies": absents_justifies,
                "absents_non_justifies": absents_non_justifies,
                "taux_presence": taux_presence,
            },
            "today": today,
        }
        
        return render(request, "professeurs/detail_cours.html", context)
        
    except Exception as e:
        print(f"Erreur dans detail_cours: {str(e)}")
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect('professeurs:mes_cours')

# =========================================
# Gestion des séances - CORRIGÉ
# =========================================

def mes_seances(request):
    """Page des séances avec filtrage"""
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        # Récupérer le professeur - CORRECTION ICI
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')
            
        today = timezone.now().date()
        
        # Récupérer les paramètres GET
        cours_id = request.GET.get('cours', '')
        groupe_id = request.GET.get('groupe', '')
        periode = request.GET.get('periode', 'toutes')
        
        # Tous les cours du professeur
        tous_cours = Cours.objects.filter(professeur=prof).order_by('libelle')
        
        # Base query pour les séances
        seances_query = Seance.objects.filter(cours__professeur=prof)
        
        # Variables pour les filtres sélectionnés
        selected_cours = None
        selected_groupe = None
        
        # Appliquer les filtres
        if cours_id and cours_id != '':
            try:
                selected_cours = Cours.objects.get(id=int(cours_id), professeur=prof)
                seances_query = seances_query.filter(cours=selected_cours)
            except (ValueError, Cours.DoesNotExist):
                cours_id = ''
        
        if groupe_id and groupe_id != '':
            try:
                selected_groupe = Groupe.objects.get(id=int(groupe_id))
                seances_query = seances_query.filter(groupe=selected_groupe)
            except (ValueError, Groupe.DoesNotExist):
                groupe_id = ''
        
        # Appliquer le filtre de période
        if periode == 'aujourdhui':
            seances_query = seances_query.filter(date=today)
        elif periode == 'semaine':
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            seances_query = seances_query.filter(date__range=[start_of_week, end_of_week])
        elif periode == 'mois':
            seances_query = seances_query.filter(date__month=today.month, date__year=today.year)
        elif periode == 'a_venir':
            seances_query = seances_query.filter(date__gte=today)
        elif periode == 'passees':
            seances_query = seances_query.filter(date__lt=today)
        
        # Obtenir les séances finales
        seances = seances_query.select_related('cours', 'groupe').order_by('-date', 'heure_debut')
        
        # Tous les groupes
        tous_groupes = Groupe.objects.filter(
            seances__cours__professeur=prof
        ).distinct().order_by('nom')
        
        # Statistiques globales
        seances_base = Seance.objects.filter(cours__professeur=prof)
        
        # Compter les séances par catégorie
        seances_a_venir_count = seances_base.filter(date__gt=today).count()
        seances_aujourdhui_count = seances_base.filter(date=today).count()
        seances_passees_count = seances_base.filter(date__lt=today).count()
        
        # Séances de la semaine
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        seances_semaine = seances_base.filter(
            date__range=[start_of_week, end_of_week]
        ).select_related('cours', 'groupe').order_by('date', 'heure_debut')
        
        # Grouper les séances de la semaine par jour
        seances_semaine_grouped = []
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            seances_jour = seances_semaine.filter(date=day)
            if seances_jour.exists():
                seances_semaine_grouped.append({
                    'date': day,
                    'seances': list(seances_jour),
                    'count': seances_jour.count()
                })
        
        # Vérifier si des présences existent
        for seance in seances:
            seance.presences_taken = Presence.objects.filter(seance=seance).exists()
        
        # Contexte
        context = {
            "prof": prof,
            "utilisateur": prof.utilisateur,
            "today": today,
            "tous_cours": tous_cours,
            "tous_groupes": tous_groupes,
            "selected_cours": selected_cours,
            "selected_groupe": selected_groupe,
            "selected_periode": periode,
            "selected_cours_id": str(cours_id) if cours_id else '',
            "selected_groupe_id": str(groupe_id) if groupe_id else '',
            "seances": list(seances),
            "total_seances": seances.count(),
            "seances_a_venir": seances_a_venir_count,
            "seances_aujourdhui": seances_aujourdhui_count,
            "seances_passees": seances_passees_count,
            "seances_semaine": list(seances_semaine),
            "seances_semaine_grouped": seances_semaine_grouped,
            "start_of_week": start_of_week,
            "end_of_week": end_of_week,
        }
        
        return render(request, "professeurs/mes_seances.html", context)
        
    except Exception as e:
        print(f"ERROR dans mes_seances: {str(e)}")
        
        # Version de secours
        try:
            prof = get_professeur_from_user_id(user_id)
            if prof:
                context = {
                    "prof": prof,
                    "utilisateur": prof.utilisateur,
                    "today": timezone.now().date(),
                    "seances": [],
                    "tous_cours": [],
                    "tous_groupes": [],
                    "seances_semaine": [],
                    "seances_semaine_grouped": [],
                    "total_seances": 0,
                    "seances_a_venir": 0,
                    "seances_aujourdhui": 0,
                    "seances_passees": 0,
                    "error": str(e),
                }
                messages.error(request, f"Erreur technique: {str(e)}")
                return render(request, "professeurs/mes_seances.html", context)
        except Exception:
            pass
        
        return redirect('/login/')

# =========================================
# Gestion des présences - CORRIGÉ
# =========================================

def prendre_presences(request, seance_id):
    """
    Prendre les présences pour une séance spécifique
    """
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')
        
        # Récupérer la séance
        seance = Seance.objects.get(id=seance_id, cours__professeur=prof)
        cours = seance.cours
        groupe = seance.groupe
        
        # Récupérer les étudiants du groupe
        etudiants_du_groupe = Etudiant.objects.filter(
            etudiantgroupe__groupe=groupe
        ).select_related('utilisateur').order_by('utilisateur__nom', 'utilisateur__prenom')
        
        # Récupérer les présences existantes
        presences_existantes = Presence.objects.filter(seance=seance)
        presences_dict = {p.etudiant_id: p for p in presences_existantes}
        
        # Trouver la date de dernière mise à jour
        date_derniere_mise_a_jour = None
        if presences_existantes.exists():
            date_derniere_mise_a_jour = presences_existantes.aggregate(
                Max('date_saisie')
            )['date_saisie__max']
        
        if request.method == 'POST':
            from django.db import transaction
            with transaction.atomic():
                for etudiant in etudiants_du_groupe:
                    statut_key = f"statut_{etudiant.id}"
                    statut = request.POST.get(statut_key, 'ABSENT_NON_JUSTIFIE')
                    
                    if statut == 'ABSENT':
                        statut = 'ABSENT_NON_JUSTIFIE'
                    
                    if etudiant.id in presences_dict:
                        presence = presences_dict[etudiant.id]
                        presence.statut = statut
                        presence.date_saisie = timezone.now()
                        presence.save()
                    else:
                        Presence.objects.create(
                            statut=statut,
                            etudiant=etudiant,
                            seance=seance,
                            date_saisie=timezone.now()
                        )
            
            messages.success(request, f"Les présences pour {cours.libelle} ont été enregistrées avec succès !")
            return redirect('professeurs:prendre_presences', seance_id=seance_id)
        
        # Préparer les données pour le template
        etudiants_data = []
        for etudiant in etudiants_du_groupe:
            presence = presences_dict.get(etudiant.id)
            
            statut = presence.statut if presence else None
            statut_affichage = statut
            if statut == 'ABSENT_NON_JUSTIFIE':
                statut_affichage = 'ABSENT'
            
            etudiants_data.append({
                'etudiant': etudiant,
                'presence': presence,
                'statut': statut,
                'statut_affichage': statut_affichage,
            })
        
        context = {
            'prof': prof,
            'utilisateur': prof.utilisateur,
            'seance': seance,
            'cours': cours,
            'groupe': groupe,
            'etudiants_data': etudiants_data,
            'presences_existantes': presences_existantes.exists(),
            'date_derniere_mise_a_jour': date_derniere_mise_a_jour,
            'today': timezone.now().date(),
        }
        
        return render(request, "professeurs/prendre_presences.html", context)
        
    except Seance.DoesNotExist:
        messages.error(request, "Séance non trouvée ou vous n'êtes pas autorisé")
        return redirect("professeurs:dashboard_professeur")
    except Exception as e:
        print(f"Erreur dans prendre_presences: {e}")
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect('professeurs:prendre_presences', seance_id=seance_id)

# =========================================
# Gestion des justifications - CORRIGÉ
# =========================================

def justifications_attente(request):
    """
    Affiche toutes les justifications en attente de validation
    """
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')
        
        statut_filter = request.GET.get('statut', 'EN_ATTENTE')
        
        base_queryset = Presence.objects.filter(
            seance__cours__professeur=prof
        ).select_related(
            'etudiant__utilisateur',
            'seance__cours',
            'seance__groupe'
        ).order_by('-date_saisie')
        
        if statut_filter == 'ACCEPTEE':
            justifications = base_queryset.filter(statut_justification='ACCEPTEE')
            titre = "Justifications acceptées"
        elif statut_filter == 'REFUSEE':
            justifications = base_queryset.filter(statut_justification='REFUSEE')
            titre = "Justifications refusées"
        elif statut_filter == 'TRAITEES':
            justifications = base_queryset.filter(
                statut_justification__in=['ACCEPTEE', 'REFUSEE']
            )
            titre = "Justifications traitées"
        elif statut_filter == 'TOUS':
            # Montrer toutes les présences ayant un statut de justification défini
            justifications = base_queryset.filter(statut_justification__in=['EN_ATTENTE', 'ACCEPTEE', 'REFUSEE'])
            titre = "Toutes les justifications"
        else:
            # Par défaut, on montre les justifications en attente
            justifications = base_queryset.filter(statut_justification='EN_ATTENTE')
            titre = "Justifications en attente"
        
        justifications_list = []
        for presence in justifications:
            # Déterminer de manière robuste si un fichier est présent
            has_file = False
            try:
                blob = getattr(presence, 'fichier_justificatif', None)
                if blob:
                    if hasattr(blob, 'tobytes'):
                        b = blob.tobytes()
                    elif isinstance(blob, bytes):
                        b = blob
                    elif isinstance(blob, memoryview):
                        b = blob.tobytes()
                    else:
                        try:
                            b = bytes(blob)
                        except Exception:
                            b = None
                    has_file = bool(b)
            except Exception:
                has_file = False

            item = {
                'presence': presence,
                'has_file': has_file
            }
            justifications_list.append(item)
        
        total_en_attente = base_queryset.filter(
            statut_justification='EN_ATTENTE'
        ).count()
        
        total_traitees = base_queryset.filter(
            statut_justification__in=['ACCEPTEE', 'REFUSEE']
        ).count()
        
        context = {
            'prof': prof,
            'utilisateur': prof.utilisateur,
            'justifications': justifications_list,
            'titre': titre,
            'statut_filter': statut_filter,
            'total_en_attente': total_en_attente,
            'total_traitees': total_traitees,
            'today': timezone.now().date(),
        }
        
        return render(request, "professeurs/justifications_attente.html", context)
        
    except Exception as e:
        print(f"Erreur dans justifications_attente: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        # Rendre la page des justifications avec données vides pour éviter une redirection silencieuse
        context = {
            'prof': None,
            'utilisateur': None,
            'justifications': [],
            'titre': 'Justifications',
            'statut_filter': request.GET.get('statut', 'EN_ATTENTE'),
            'total_en_attente': 0,
            'total_traitees': 0,
            'today': timezone.now().date(),
            'error': str(e)
        }
        return render(request, "professeurs/justifications_attente.html", context)

# ... (les autres fonctions restent similaires mais utilisent get_professeur_from_user_id) ...

def voir_justification(request, presence_id):
    """
    Voir les détails d'une justification
    """
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')
        
        presence = Presence.objects.select_related(
            'etudiant__utilisateur',
            'seance__cours',
            'seance__groupe'
        ).get(
            id=presence_id,
            seance__cours__professeur=prof
        )
        
        fichier_justificatif = None
        if presence.fichier_justificatif:
            # normalize bytes safely
            if hasattr(presence.fichier_justificatif, 'tobytes'):
                fichier_bytes = presence.fichier_justificatif.tobytes()
            elif isinstance(presence.fichier_justificatif, bytes):
                fichier_bytes = presence.fichier_justificatif
            elif isinstance(presence.fichier_justificatif, memoryview):
                fichier_bytes = presence.fichier_justificatif.tobytes()
            else:
                try:
                    fichier_bytes = bytes(presence.fichier_justificatif)
                except Exception:
                    fichier_bytes = None

            if fichier_bytes:
                fichier_base64 = base64.b64encode(fichier_bytes).decode('utf-8')
                fichier_type = detecter_type_fichier(fichier_bytes)
                fichier_justificatif = {
                    'data': fichier_base64,
                    'type': fichier_type,
                    'has_file': True
                }
            else:
                fichier_justificatif = {'has_file': False}
        else:
            fichier_justificatif = {
                'has_file': False
            }
        
        context = {
            'prof': prof,
            'utilisateur': prof.utilisateur,
            'presence': presence,
            'fichier_justificatif': fichier_justificatif,
            'today': timezone.now().date(),
        }
        
        return render(request, "professeurs/voir_justification.html", context)
        
    except Presence.DoesNotExist:
        messages.error(request, "Justification non trouvée")
        return redirect('professeurs:justifications_attente')
    except Exception as e:
        print(f"Erreur dans voir_justification: {e}")
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect('professeurs:justifications_attente')

# ... (continuez avec les autres fonctions en utilisant la même correction) ...

def traiter_justification(request, presence_id):
    """
    Traiter une justification (accepter ou refuser)
    """
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    if request.method == 'POST':
        try:
            prof = get_professeur_from_user_id(user_id)
            if not prof:
                messages.error(request, "Professeur non trouvé")
                return redirect('/login/')
            
            # Allow processing even if the presence status has changed; authorize by professor ownership only
            presence = Presence.objects.get(
                id=presence_id,
                seance__cours__professeur=prof
            )
            
            action = (request.POST.get('action') or '').lower()
            commentaire_prof = request.POST.get('commentaire_prof', '').strip()

            # Prevent double-processing
            if presence.statut_justification in ['ACCEPTEE', 'REFUSEE']:
                messages.info(request, "Cette justification a déjà été traitée.")
                return redirect('professeurs:justifications_attente')

            if action == 'accepter':
                presence.statut_justification = 'ACCEPTEE'
                message = f"La justification de {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom} a été acceptée."
                message_type = 'success'
            elif action == 'refuser':
                # Require a comment for refusals
                if not commentaire_prof:
                    messages.error(request, "Le commentaire est requis pour un refus.")
                    return redirect('professeurs:justifications_attente')
                presence.statut_justification = 'REFUSEE'
                presence.statut = 'ABSENT_NON_JUSTIFIE'
                message = f"La justification de {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom} a été refusée."
                message_type = 'warning'
            else:
                messages.error(request, "Action non valide")
                return redirect('professeurs:justifications_attente')
            
            presence.commentaire_professeur = commentaire_prof
            presence.date_traitement = timezone.now()
            presence.save()
            
            if message_type == 'success':
                messages.success(request, message)
            else:
                messages.warning(request, message)
            
        except Presence.DoesNotExist:
            messages.error(request, "Justification non trouvée ou vous n'êtes pas autorisé")
        except Exception as e:
            print(f"Erreur dans traiter_justification: {e}")
            messages.error(request, f"Une erreur est survenue: {str(e)}")
    
    return redirect('professeurs:justifications_attente')

# ... (les fonctions pour les fichiers restent similaires) ...
# =========================================
# Fichiers justificatifs
# =========================================

def telecharger_fichier_justificatif(request, presence_id):
    """
    Télécharger un fichier justificatif
    """
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        # Récupérer le professeur pour vérifier l'autorisation
        prof = get_professeur_from_user_id(user_id)
        if not prof:
            messages.error(request, "Professeur non trouvé")
            return redirect('/login/')

        presence = Presence.objects.get(
            id=presence_id,
            seance__cours__professeur=prof
        )
        
        if not presence.fichier_justificatif:
            messages.error(request, "Aucun fichier justificatif disponible")
            return redirect('professeurs:justifications_attente')
        
        fichier_bytes, was_base64 = normalize_file_bytes(presence.fichier_justificatif)
        if not fichier_bytes:
            messages.error(request, "Aucun fichier justificatif disponible")
            return redirect('professeurs:justifications_attente')

        # Détecter le type à partir des octets et forcer PDF si le header PDF est trouvé
        fichier_type = detecter_type_fichier(fichier_bytes)
        if fichier_type == 'application/octet-stream' and b'%PDF' in fichier_bytes[:512]:
            fichier_type = 'application/pdf'

        response = HttpResponse(
            fichier_bytes,
            content_type=fichier_type
        )
        
        filename = f"justificatif_{presence.etudiant.code_etudiant}_{presence.seance.date.strftime('%Y%m%d')}"
        
        if fichier_type == 'image/png':
            filename += '.png'
        elif fichier_type == 'image/jpeg':
            filename += '.jpg'
        elif fichier_type == 'application/pdf':
            filename += '.pdf'
        elif fichier_type == 'application/zip':
            filename += '.zip'
        elif fichier_type == 'application/msword':
            filename += '.doc'
        elif fichier_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            filename += '.docx'
        else:
            filename += '.dat'
            
        # Add debug headers so the browser's network panel reveals detected type and size
        try:
            response['X-Detected-Type'] = fichier_type
            response['X-Bytes-Length'] = str(len(fichier_bytes))
            response['X-Presence-ID'] = str(presence.id)
        except Exception:
            pass

        # If requested for inline viewing (e.g. preview iframe), send inline content-disposition
        if request.GET.get('inline') == '1':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Presence.DoesNotExist:
        messages.error(request, "Fichier non trouvé ou vous n'êtes pas autorisé")
        return redirect('professeurs:justifications_attente')
    except Exception as e:
        print(f"Erreur dans telecharger_fichier_justificatif: {e}")
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect('professeurs:justifications_attente')

def afficher_fichier(request, presence_id):
    """
    Afficher un fichier dans un nouvel onglet
    """
    user_id = check_professor_auth(request)
    if not user_id:
        return redirect('/login/')
    
    try:
        prof = Professeur.objects.get(utilisateur_id=user_id)
        
        presence = Presence.objects.get(
            id=presence_id,
            seance__cours__professeur=prof
        )
        
        if not presence.fichier_justificatif:
            messages.error(request, "Aucun fichier justificatif disponible")
            return redirect('professeurs:justifications_attente')
        
        fichier_bytes, was_base64 = normalize_file_bytes(presence.fichier_justificatif)
        if not fichier_bytes:
            messages.error(request, "Aucun fichier justificatif disponible")
            return redirect('professeurs:justifications_attente')

        fichier_type = detecter_type_fichier(fichier_bytes)
        # If detecter fell back to octet-stream but content indicates PDF, force it
        if fichier_type == 'application/octet-stream' and b'%PDF' in fichier_bytes[:512]:
            fichier_type = 'application/pdf'

        fichier_base64 = base64.b64encode(fichier_bytes).decode('utf-8')
        
        if fichier_type == 'application/pdf':
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Justificatif - {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom}</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        background-color: #f8f9fa;
                    }}
                    .header {{
                        background-color: #343a40;
                        color: white;
                        padding: 15px 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }}
                    .header h1 {{
                        font-size: 1.5rem;
                        margin: 0;
                    }}
                    .file-container {{
                        height: calc(100vh - 80px);
                        padding: 20px;
                    }}
                    iframe {{
                        width: 100%;
                        height: 100%;
                        border: none;
                        border-radius: 5px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <div>
                        <h1>
                            <i class="bi bi-file-earmark"></i>
                            Justificatif: {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom}
                        </h1>
                        <small>
                            {presence.seance.cours.libelle} • {presence.seance.date|date:"d/m/Y"}
                        </small>
                    </div>
                    <div class="btn-group">
                        <a href="/professeurs/justifications/{presence.id}/telecharger/" 
                           class="btn btn-danger" 
                           download
                           style="color: white; text-decoration: none; background-color: #dc3545; padding: 8px 15px; border-radius: 4px;">
                            <i class="bi bi-download"></i> Télécharger
                        </a>
                        <button onclick="window.close()" class="btn btn-secondary ms-2">
                            <i class="bi bi-x-circle"></i> Fermer
                        </button>
                    </div>
                </div>
                <div class="file-container">
                    <iframe src="/professeurs/justifications/{presence.id}/telecharger/?inline=1"></iframe>
                </div>
            </body>
            </html>
            '''
            return HttpResponse(html)
        
        elif fichier_type.startswith('image/'):
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Justificatif - {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom}</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        background-color: #2c3e50;
                    }}
                    .header {{
                        background-color: #343a40;
                        color: white;
                        padding: 15px 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }}
                    .header h1 {{
                        font-size: 1.5rem;
                        margin: 0;
                    }}
                    .image-container {{
                        padding: 20px;
                        height: calc(100vh - 80px);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        overflow: auto;
                    }}
                    .image-wrapper {{
                        max-width: 100%;
                        max-height: 100%;
                        text-align: center;
                    }}
                    .image-wrapper img {{
                        max-width: 100%;
                        max-height: 80vh;
                        object-fit: contain;
                        border-radius: 5px;
                        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <div>
                        <h1>
                            <i class="bi bi-image"></i>
                            Image justificative: {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom}
                        </h1>
                        <small>
                            {presence.seance.cours.libelle} • {presence.seance.date|date:"d/m/Y"}
                        </small>
                    </div>
                    <div class="btn-group">
                        <a href="/professeurs/justifications/{presence.id}/telecharger/" 
                           class="btn btn-primary" 
                           download
                           style="color: white; text-decoration: none; padding: 8px 15px; border-radius: 4px;">
                            <i class="bi bi-download"></i> Télécharger
                        </a>
                        <button onclick="window.close()" class="btn btn-secondary ms-2">
                            <i class="bi bi-x-circle"></i> Fermer
                        </button>
                    </div>
                </div>
                <div class="image-container">
                    <div class="image-wrapper">
                        <img src="/professeurs/justifications/{presence.id}/telecharger/?inline=1" 
                             alt="Fichier justificatif">
                    </div>
                </div>
            </body>
            </html>
            '''
            return HttpResponse(html)
        
        else:
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Justificatif - {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom}</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        background-color: #f8f9fa;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .container {{
                        max-width: 800px;
                        padding: 30px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="card shadow">
                        <div class="card-header bg-info text-white">
                            <h4 class="mb-0">
                                <i class="bi bi-file-earmark"></i> Fichier justificatif
                            </h4>
                        </div>
                        <div class="card-body text-center">
                            <i class="bi bi-file-earmark-binary" style="font-size: 4rem; color: #6c757d;"></i>
                            <h5 class="mt-3">Fichier justificatif</h5>
                            <p class="text-muted">
                                Étudiant: {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom}<br>
                                Cours: {presence.seance.cours.libelle}<br>
                                Date: {presence.seance.date|date:"d/m/Y"}<br>
                                Type: {fichier_type}<br>
                                Taille: {len(fichier_bytes)} octets
                            </p>
                            <div class="mt-4">
                                <a href="/professeurs/justifications/{presence.id}/telecharger/" 
                                   class="btn btn-primary" 
                                   download>
                                    <i class="bi bi-download"></i> Télécharger le fichier
                                </a>
                                <button onclick="window.close()" class="btn btn-secondary ms-2">
                                    <i class="bi bi-x-circle"></i> Fermer
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
            return HttpResponse(html)
        
    except Presence.DoesNotExist:
        return HttpResponse('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Erreur</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="alert alert-danger">
                        <h4><i class="bi bi-exclamation-triangle"></i> Fichier non trouvé</h4>
                        <p>Le fichier demandé n'existe pas ou vous n'êtes pas autorisé à y accéder.</p>
                        <button onclick="window.close()" class="btn btn-secondary">Fermer</button>
                    </div>
                </div>
            </body>
            </html>
        ''')
    except Exception as e:
        return HttpResponse(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Erreur</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="alert alert-danger">
                        <h4><i class="bi bi-exclamation-triangle"></i> Erreur technique</h4>
                        <p>{str(e)}</p>
                        <button onclick="window.close()" class="btn btn-secondary">Fermer</button>
                    </div>
                </div>
            </body>
            </html>
        ''')

def afficher_fichier_modal(request, presence_id):
    """
    Afficher un fichier dans une modal
    """
    user_id = check_professor_auth(request)
    if not user_id:
        return HttpResponse("Non autorisé", status=401)
    
    try:
        prof = Professeur.objects.get(utilisateur_id=user_id)
        
        presence = Presence.objects.get(
            id=presence_id,
            seance__cours__professeur=prof
        )
        
        if not presence.fichier_justificatif:
            return HttpResponse('''
                <div class="alert alert-warning text-center">
                    <i class="bi bi-exclamation-triangle fs-1"></i>
                    <h5>Aucun fichier disponible</h5>
                    <p>Aucun fichier justificatif n'a été joint.</p>
                </div>
            ''')
        
        try:
            fichier_bytes, was_base64 = normalize_file_bytes(presence.fichier_justificatif)
            if not fichier_bytes:
                return HttpResponse('''
                    <div class="alert alert-warning text-center">
                        <i class="bi bi-exclamation-triangle fs-1"></i>
                        <h5>Fichier introuvable ou vide</h5>
                        <p>Le fichier justificatif est invalide ou vide.</p>
                        <a href="/professeurs/justifications/{}/telecharger/" class="btn btn-primary">Télécharger</a>
                    </div>
                '''.format(presence.id))

            fichier_base64 = base64.b64encode(fichier_bytes).decode('utf-8')
            fichier_type = detecter_type_fichier(fichier_bytes)
            if fichier_type == 'application/octet-stream' and b'%PDF' in fichier_bytes[:512]:
                fichier_type = 'application/pdf'

            # Mode debug (optionnel) : si ?debug=1 alors on affiche des infos techniques
            if request.GET.get('debug') == '1':
                hex_snippet = fichier_bytes[:32].hex() if fichier_bytes else ''
                debug_html = f'''
                <div class="p-3">
                    <h5>DEBUG — informations fichier</h5>
                    <ul>
                        <li>presence.id: {presence.id}</li>
                        <li>taille (octets): {len(fichier_bytes)}</li>
                        <li>type détecté: {fichier_type}</li>
                        <li>longueur base64: {len(fichier_base64)}</li>
                        <li>hex (premiers 32 octets): {hex_snippet}</li>
                    </ul>
                    <div class="mt-3">
                        <a href="/professeurs/justifications/{presence.id}/telecharger/" class="btn btn-primary">Télécharger</a>
                    </div>
                </div>
                '''
                return HttpResponse(debug_html)

        except Exception as e:
            return HttpResponse(f'''
                <div class="text-center">
                    <div class="alert alert-info">
                        <i class="bi bi-file-earmark fs-1"></i>
                        <h5>Fichier justificatif</h5>
                        <p>Fichier disponible en téléchargement.</p>
                        <a href="/professeurs/justifications/{presence.id}/telecharger/" 
                           class="btn btn-primary" 
                           download="justificatif_{presence.etudiant.code_etudiant}">
                            <i class="bi bi-download"></i> Télécharger
                        </a>
                    </div>
                </div>
            ''')
        
        embed_html = ''
        if fichier_type.startswith('image/'):
            # Use the streaming endpoint for images to avoid embedding huge data URIs
            img_src = f"/professeurs/justifications/{presence.id}/telecharger/?inline=1"
            embed_html = f'''
                <div class="text-center">
                    <img src="{img_src}" 
                         class="img-fluid rounded border" 
                         alt="Fichier justificatif"
                         style="max-height: 300px;">
                </div>
            '''
            html_content = f'''
            <div class="text-center">
                <img src="{img_src}" 
                     class="img-fluid rounded border" 
                     alt="Fichier justificatif"
                     style="max-height: 70vh;">
                <div class="mt-3">
                    <a href="/professeurs/justifications/{presence.id}/telecharger/" 
                       class="btn btn-sm btn-primary" 
                       download="justificatif_{presence.etudiant.code_etudiant}.{fichier_type.split('/')[-1]}">
                        <i class="bi bi-download"></i> Télécharger
                    </a>
                </div>
            </div>
            '''
        elif fichier_type == 'application/pdf':
            # Use streaming endpoint for PDFs to avoid extremely large data URIs which can fail
            pdf_src = f"/professeurs/justifications/{presence.id}/telecharger/?inline=1"
            embed_html = f'''
                <div class="pdf-embed" style="height: 30vh;">
                    <iframe 
                        src="{pdf_src}" 
                        width="100%" 
                        height="100%" 
                        frameborder="0"
                        style="border: none;">
                        Votre navigateur ne supporte pas l'affichage des PDF.
                    </iframe>
                </div>
            '''
            html_content = f'''
            <div class="pdf-viewer-container">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="mb-0">
                        <i class="bi bi-file-pdf text-danger"></i> Document PDF
                    </h5>
                    <div class="btn-group">
                        <a href="/professeurs/justifications/{presence.id}/telecharger/" 
                           class="btn btn-sm btn-danger" 
                           download="justificatif_{presence.etudiant.code_etudiant}.pdf">
                            <i class="bi bi-download"></i> Télécharger
                        </a>
                    </div>
                </div>
                
                <div class="border rounded" style="height: 70vh;">
                    <iframe 
                        src="{pdf_src}" 
                        width="100%" 
                        height="100%" 
                        frameborder="0"
                        style="border: none;">
                        Votre navigateur ne supporte pas l'affichage des PDF.
                    </iframe>
                </div>
            </div>
            '''
        else:
            embed_html = f'''
                <div class="text-center p-2">
                    <i class="bi bi-file-earmark fs-1"></i>
                    <p class="small mb-0">Type: {fichier_type}</p>
                    <small class="text-muted">Taille: {len(fichier_bytes)} bytes</small>
                    <div class="mt-2">
                        <a href="/professeurs/justifications/{presence.id}/telecharger/" class="btn btn-sm btn-primary">Télécharger</a>
                    </div>
                </div>
            '''
            html_content = f'''
            <div class="text-center">
                <div class="alert alert-info">
                    <i class="bi bi-file-earmark fs-1"></i>
                    <h5>Fichier justificatif</h5>
                    <p>Type: {fichier_type}</p>
                    <p>Taille: {len(fichier_bytes)} bytes</p>
                    <div class="mt-3">
                        <a href="/professeurs/justifications/{presence.id}/telecharger/" 
                           class="btn btn-primary" 
                           download="justificatif_{presence.etudiant.code_etudiant}">
                            <i class="bi bi-download"></i> Télécharger
                        </a>
                    </div>
                </div>
            </div>
            '''
        
        # If embed requested, return only the lightweight embed HTML (for inline preview)
        if request.GET.get('embed') == '1':
            return HttpResponse(embed_html)

        return HttpResponse(html_content)
        
    except Presence.DoesNotExist:
        return HttpResponse('''
            <div class="alert alert-danger text-center">
                <i class="bi bi-exclamation-triangle fs-1"></i>
                <h5>Fichier non trouvé</h5>
                <p>Le fichier demandé n'existe pas ou vous n'êtes pas autorisé.</p>
            </div>
        ''')
    except Exception as e:
        print(f"DEBUG: Erreur générale: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f'''
            <div class="alert alert-danger text-center">
                <i class="bi bi-exclamation-triangle fs-1"></i>
                <h5>Erreur technique</h5>
                <p>{str(e)}</p>
            </div>
        ''')


# --- Diagnostic endpoints for debugging PDF display issues ---
def test_pdf(request):
    """Return a tiny, valid PDF for browser rendering tests."""
    pdf_bytes = b"%PDF-1.1\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj\n4 0 obj << /Length 44 >> stream\nBT /F1 24 Tf 50 100 Td (Test) Tj ET\nendstream endobj\n5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000116 00000 n \n0000000178 00000 n \n0000000235 00000 n \ntrailer << /Size 6 /Root 1 0 R >>\nstartxref\n308\n%%EOF"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="test.pdf"'
    response['X-Dbg-Test'] = 'ok'
    return response


def presence_file_info(request, presence_id):
    """Return JSON diagnostics for a presence's stored file."""
    try:
        p = Presence.objects.get(id=presence_id)
    except Presence.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)

    data, was_b64 = normalize_file_bytes(p.fichier_justificatif)
    size = len(data) if data else 0
    detected = detecter_type_fichier(data) if data else 'none'
    starts = data[:32].hex() if data else ''
    return JsonResponse({
        'presence': presence_id,
        'size': size,
        'detected_type': detected,
        'was_base64': was_b64,
        'starts_hex': starts,
    })


def presence_stats(request):
    """Return counts per justification status for the logged-in professor."""
    user_id = check_professor_auth(request)
    if not user_id:
        return JsonResponse({'error': 'not authenticated'}, status=401)
    prof = get_professeur_from_user_id(user_id)
    if not prof:
        return JsonResponse({'error': 'professeur not found'}, status=404)

    base = Presence.objects.filter(seance__cours__professeur=prof)
    presents = base.filter(statut='PRESENT').count()
    absents_just = base.filter(statut='ABSENT_JUSTIFIE').count()
    absents_non = base.filter(statut='ABSENT_NON_JUSTIFIE').count()
    total_pres = base.count()

    return JsonResponse({
        'en_attente': base.filter(statut_justification='EN_ATTENTE').count(),
        'acceptee': base.filter(statut_justification='ACCEPTEE').count(),
        'refusee': base.filter(statut_justification='REFUSEE').count(),
        'traitees': base.filter(statut_justification__in=['ACCEPTEE', 'REFUSEE']).count(),
        'total': total_pres,
        'presents': presents,
        'absents_justifies': absents_just,
        'absents_non_justifies': absents_non,
        'taux_presence': round((presents / total_pres * 100), 2) if total_pres else 0,
    })