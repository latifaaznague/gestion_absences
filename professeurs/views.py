from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
import requests
import json

# =========================================
# Login professeur (Version simplifiée)
# =========================================
def login_view(request):
    """
    Gère la connexion des professeurs - Version simplifiée
    """
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        # Pour l'instant, utiliser une connexion directe sans RPC
        from Home.models import Utilisateur, Professeur
        
        try:
            # Chercher l'utilisateur
            utilisateur = Utilisateur.objects.get(
                email=email,
                type_utilisateur='PROFESSEUR'
            )
            
            # Vérifier le mot de passe (en clair, comme dans la base)
            if utilisateur.mot_de_passe != password:
                messages.error(request, "Mot de passe incorrect")
                return render(request, "professeurs/login.html")
            
            # Chercher le professeur
            professeur = Professeur.objects.get(utilisateur=utilisateur)
            
            # Stocker en session
            request.session['professeur_id'] = professeur.utilisateur.id
            request.session['nom'] = utilisateur.nom
            request.session['prenom'] = utilisateur.prenom
            request.session['specialite'] = professeur.specialite or ""
            
            messages.success(request, f"Connexion réussie ! Bienvenue {utilisateur.prenom}.")
            return redirect('professeurs:dashboard_professeur')
            
        except Utilisateur.DoesNotExist:
            messages.error(request, "Email incorrect ou utilisateur non professeur")
        except Professeur.DoesNotExist:
            messages.error(request, "Compte professeur non trouvé")
        except Exception as e:
            messages.error(request, f"Erreur technique: {str(e)}")
    
    # Si déjà connecté, rediriger
    if 'professeur_id' in request.session:
        return redirect('professeurs:dashboard_professeur')
    
    return render(request, "professeurs/login.html")

# =========================================
# Dashboard professeur (Version simplifiée)
# =========================================
def dashboard_professeur(request):
    """
    Affiche le tableau de bord du professeur
    """
    professeur_id = request.session.get("professeur_id")
    if not professeur_id:
        return redirect("professeurs:login_view")

    try:
        from Home.models import Professeur, Cours, Seance, Presence
        from django.utils import timezone
        from datetime import timedelta
        
        prof = Professeur.objects.select_related('utilisateur').get(utilisateur_id=professeur_id)
    except Professeur.DoesNotExist:
        request.session.flush()
        return redirect("professeurs:login_view")

    utilisateur = prof.utilisateur
    
    # Récupérer les cours du professeur
    cours_professeur = Cours.objects.filter(professeur=prof)
    
    # Récupérer les séances prévues aujourd'hui
    today = timezone.now().date()
    seances_aujourdhui = Seance.objects.filter(
        cours__professeur=prof,
        date=today
    ).select_related('cours', 'groupe').order_by('heure_debut')
    
    # Récupérer les justifications en attente
    justifications_attente = Presence.objects.filter(
        seance__cours__professeur=prof,
        statut='ABSENT_JUSTIFIE',
        statut_justification='EN_ATTENTE'
    ).select_related(
        'etudiant__utilisateur',
        'seance__cours',
        'seance__groupe'
    ).order_by('-date_saisie')[:10]
    
    # Calculer les statistiques
    total_cours = cours_professeur.count()
    total_seances_aujourdhui = seances_aujourdhui.count()
    total_justifications_attente = justifications_attente.count()
    
    # Récupérer les séances de la semaine
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    seances_semaine = Seance.objects.filter(
        cours__professeur=prof,
        date__range=[start_of_week, end_of_week]
    ).select_related('cours', 'groupe').order_by('date', 'heure_debut')
    
    # Statistiques de présence
    total_presences = Presence.objects.filter(
        seance__cours__professeur=prof
    ).count()
    
    presents = Presence.objects.filter(
        seance__cours__professeur=prof,
        statut='PRESENT'
    ).count()
    
    absents_justifies = Presence.objects.filter(
        seance__cours__professeur=prof,
        statut='ABSENT_JUSTIFIE'
    ).count()
    
    absents_non_justifies = Presence.objects.filter(
        seance__cours__professeur=prof,
        statut='ABSENT_NON_JUSTIFIE'
    ).count()
    
    taux_presence = round((presents / total_presences * 100), 2) if total_presences > 0 else 0
    
    # Préparer le contexte
    context = {
        "prof": prof,
        "utilisateur": utilisateur,
        "cours_professeur": cours_professeur,
        "seances_aujourdhui": seances_aujourdhui,
        "seances_semaine": seances_semaine,
        "justifications_attente": justifications_attente,
        "total_cours": total_cours,
        "total_seances_aujourdhui": total_seances_aujourdhui,
        "total_seances_semaine": seances_semaine.count(),
        "total_justifications_attente": total_justifications_attente,
        "today": today,
        "start_of_week": start_of_week,
        "end_of_week": end_of_week,
        "stats": {
            "total_presences": total_presences,
            "presents": presents,
            "absents_justifies": absents_justifies,
            "absents_non_justifies": absents_non_justifies,
            "total_absences": absents_justifies + absents_non_justifies,
            "taux_presence": taux_presence
        }
    }

    return render(request, "professeurs/dashboard.html", context)
# =========================================
# Déconnexion
# =========================================
def logout_view(request):
    """
    Déconnecte le professeur
    """
    request.session.flush()
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect("professeurs:login_view")

# =========================================
# Pages en construction
# =========================================
def mes_cours(request):
    """Page des cours"""
    professeur_id = request.session.get("professeur_id")
    if not professeur_id:
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur, Cours
        prof = Professeur.objects.get(utilisateur_id=professeur_id)
        
        # Récupérer les cours du professeur
        cours_professeur = Cours.objects.filter(professeur=prof)
        
    except Professeur.DoesNotExist:
        request.session.flush()
        return redirect("professeurs:login_view")
    
    context = {
        "prof": prof,
        "utilisateur": prof.utilisateur,
        "cours_professeur": cours_professeur,  # Ajouter cette ligne
        "total_cours": cours_professeur.count(),  # Calculer le total
    }
    
    return render(request, "professeurs/mes_cours.html", context)

def justifications_attente(request):
    """Page des justifications (en construction)"""
    professeur_id = request.session.get("professeur_id")
    if not professeur_id:
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur
        prof = Professeur.objects.get(utilisateur_id=professeur_id)
    except Professeur.DoesNotExist:
        request.session.flush()
        return redirect("professeurs:login_view")
    
    context = {
        "prof": prof,
        "utilisateur": prof.utilisateur,
    }
    
    return render(request, "professeurs/justifications_attente.html", context)


#profile
def profil_professeur(request):
    """
    Affiche le profil du professeur connecté
    """
    # Vérifier si le professeur est connecté
    professeur_id = request.session.get("professeur_id")
    if not professeur_id:
        return redirect("professeurs:login_view")

    try:
        from Home.models import Professeur, Cours, Seance
        prof = Professeur.objects.select_related('utilisateur').get(utilisateur_id=professeur_id)
    except Professeur.DoesNotExist:
        request.session.flush()
        return redirect("professeurs:login_view")

    # Récupérer les statistiques
    total_cours = Cours.objects.filter(professeur=prof).count()
    total_seances = Seance.objects.filter(cours__professeur=prof).count()
    
    # Dernières modifications
    derniers_cours = Cours.objects.filter(professeur=prof).order_by('-id')[:5]
    dernieres_seances = Seance.objects.filter(cours__professeur=prof).order_by('-date', '-heure_debut')[:5]

    context = {
        "prof": prof,
        "utilisateur": prof.utilisateur,
        "total_cours": total_cours,
        "total_seances": total_seances,
        "derniers_cours": derniers_cours,
        "dernieres_seances": dernieres_seances,
        "today": timezone.now().date(),
    }

    return render(request, "professeurs/profil.html", context)


def modifier_profil(request):
    """
    Permet au professeur de modifier son profil
    """
    professeur_id = request.session.get("professeur_id")
    if not professeur_id:
        return redirect("professeurs:login_view")

    try:
        from Home.models import Professeur
        prof = Professeur.objects.select_related('utilisateur').get(utilisateur_id=professeur_id)
    except Professeur.DoesNotExist:
        request.session.flush()
        return redirect("professeurs:login_view")

    if request.method == "POST":
        # Récupérer les données du formulaire
        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()
        email = request.POST.get("email", "").strip()
        specialite = request.POST.get("specialite", "").strip()
        
        # Mettre à jour l'utilisateur
        utilisateur = prof.utilisateur
        utilisateur.nom = nom
        utilisateur.prenom = prenom
        utilisateur.email = email
        utilisateur.save()
        
        # Mettre à jour le professeur
        prof.specialite = specialite
        prof.save()
        
        # Mettre à jour la session
        request.session['nom'] = nom
        request.session['prenom'] = prenom
        request.session['specialite'] = specialite
        
        messages.success(request, "Votre profil a été mis à jour avec succès !")
        return redirect("professeurs:profil_professeur")

    context = {
        "prof": prof,
        "utilisateur": prof.utilisateur,
    }

    return render(request, "professeurs/modifier_profil.html", context)
#details_cour
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages

def detail_cours(request, cours_id):
    """Affiche les détails d'un cours spécifique"""
    professeur_id = request.session.get("professeur_id")
    if not professeur_id:
        messages.error(request, "Veuillez vous connecter")
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur, Cours, Seance, Presence
        
        # Définir today au début pour qu'il soit toujours disponible
        today = timezone.now().date()
        
        # Récupérer le professeur
        try:
            prof = Professeur.objects.get(utilisateur_id=professeur_id)
        except Professeur.DoesNotExist:
            messages.error(request, "Professeur non trouvé")
            request.session.flush()
            return redirect("professeurs:login_view")
        
        # Récupérer le cours
        try:
            cours = Cours.objects.get(id=cours_id, professeur=prof)
        except Cours.DoesNotExist:
            messages.error(request, "Cours non trouvé ou vous n'êtes pas autorisé à y accéder")
            return redirect("professeurs:mes_cours")
        
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
        etudiant_ids = set()
        for presence in presences:
            etudiant_ids.add(presence.etudiant_id)
        total_etudiants = len(etudiant_ids)
        
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
            "total_etudiants": total_etudiants,
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
        # En cas d'erreur inattendue
        print(f"Erreur dans detail_cours: {str(e)}")
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        
        # Créer un contexte minimal pour éviter l'erreur
        context = {
            "prof": None,
            "utilisateur": None,
            "cours": None,
            "seances": [],
            "total_seances": 0,
            "prochaines_seances": [],
            "seances_passees": [],
            "total_etudiants": 0,
            "statistiques": {
                "total_presences": 0,
                "presents": 0,
                "absents_justifies": 0,
                "absents_non_justifies": 0,
                "taux_presence": 0,
            },
            "today": timezone.now().date(),
            "error": str(e),
        }
        
        return render(request, "professeurs/detail_cours.html", context)
    
    #absences 

    # =========================================
# Gestion des présences depuis le dashboard
# =========================================
# Gestion des présences depuis le dashboard - VERSION AMÉLIORÉE
# =========================================
def prendre_presences(request, seance_id):
    """
    Prendre les présences pour une séance spécifique
    """
    if 'professeur_id' not in request.session:
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur, Seance, Etudiant, Presence, EtudiantGroupe
        from django.utils import timezone
        from django.db import transaction
        from django.db.models import Max
        
        prof = Professeur.objects.get(utilisateur_id=request.session['professeur_id'])
        
        # Récupérer la séance et vérifier que c'est bien le cours du professeur
        seance = Seance.objects.get(id=seance_id, cours__professeur=prof)
        cours = seance.cours
        groupe = seance.groupe
        
        # Récupérer les étudiants du groupe
        etudiants_du_groupe = Etudiant.objects.filter(
            etudiantgroupe__groupe=groupe
        ).select_related('utilisateur').order_by('utilisateur__nom', 'utilisateur__prenom')
        
        # Récupérer les présences existantes pour cette séance
        presences_existantes = Presence.objects.filter(seance=seance)
        presences_dict = {p.etudiant_id: p for p in presences_existantes}
        
        # Trouver la date de dernière mise à jour
        date_derniere_mise_a_jour = None
        if presences_existantes.exists():
            date_derniere_mise_a_jour = presences_existantes.aggregate(
                Max('date_saisie')
            )['date_saisie__max']
        
        if request.method == 'POST':
            with transaction.atomic():
                for etudiant in etudiants_du_groupe:
                    statut_key = f"statut_{etudiant.id}"
                    statut = request.POST.get(statut_key, 'ABSENT_NON_JUSTIFIE')  # Par défaut : absent non justifié
                    
                    # Convertir "ABSENT" en "ABSENT_NON_JUSTIFIE" pour la base de données
                    if statut == 'ABSENT':
                        statut = 'ABSENT_NON_JUSTIFIE'
                    
                    if etudiant.id in presences_dict:
                        # Mettre à jour la présence existante
                        presence = presences_dict[etudiant.id]
                        presence.statut = statut
                        presence.date_saisie = timezone.now()
                        presence.save()
                    else:
                        # Créer une nouvelle présence
                        Presence.objects.create(
                            statut=statut,
                            etudiant=etudiant,
                            seance=seance,
                            date_saisie=timezone.now()
                        )
            
            messages.success(request, f"Les présences pour {cours.libelle} ont été enregistrées avec succès !")
            return redirect('professeurs:prendre_presences', seance_id=seance_id)  # Rediriger vers la même page
        
        # Préparer les données pour le template
        etudiants_data = []
        for etudiant in etudiants_du_groupe:
            presence = presences_dict.get(etudiant.id)
            
            # Déterminer le statut à afficher
            statut = presence.statut if presence else None
            # Convertir pour l'affichage dans le template
            statut_affichage = statut
            if statut == 'ABSENT_NON_JUSTIFIE':
                statut_affichage = 'ABSENT'  # Pour l'affichage simplifié
            
            etudiants_data.append({
                'etudiant': etudiant,
                'presence': presence,
                'statut': statut,  # Pour le traitement
                'statut_affichage': statut_affichage,  # Pour l'affichage
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
# Gestion des justifications
# =========================================
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.db import transaction
import base64

# =========================================
# Fonction utilitaire pour détecter le type de fichier
# =========================================
def detecter_type_fichier(fichier_data):
    """
    Détecter le type de fichier à partir des données
    """
    if not fichier_data:
        return 'application/octet-stream'
    
    try:
        if hasattr(fichier_data, 'tobytes'):
            fichier_bytes = fichier_data.tobytes()
        elif isinstance(fichier_data, bytes):
            fichier_bytes = fichier_data
        elif isinstance(fichier_data, bytearray):
            fichier_bytes = bytes(fichier_data)
        elif isinstance(fichier_data, memoryview):
            fichier_bytes = fichier_data.tobytes()
        else:
            fichier_bytes = bytes(fichier_data)
    except Exception as e:
        print(f"Erreur de conversion en bytes: {e}")
        return 'application/octet-stream'
    
    if len(fichier_bytes) < 4:
        return 'application/octet-stream'
    
    try:
        if fichier_bytes[:4] == b'\x89PNG':
            return 'image/png'
        elif fichier_bytes[:2] == b'\xff\xd8':
            return 'image/jpeg'
        elif fichier_bytes[:4] == b'%PDF':
            return 'application/pdf'
        elif fichier_bytes[:2] == b'PK':
            return 'application/zip'
        elif fichier_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            return 'application/msword'
        elif fichier_bytes[:2] == b'PK' and b'[Content_Types].xml' in fichier_bytes[:1000]:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            return 'application/octet-stream'
    except Exception as e:
        print(f"Erreur de détection de type: {e}")
        return 'application/octet-stream'

# =========================================
# Téléchargement de fichier justificatif
# =========================================
def telecharger_fichier_justificatif(request, presence_id):
    """
    Télécharger un fichier justificatif
    """
    if 'professeur_id' not in request.session:
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur, Presence
        prof = Professeur.objects.get(utilisateur_id=request.session['professeur_id'])
        
        presence = Presence.objects.get(
            id=presence_id,
            seance__cours__professeur=prof
        )
        
        if not presence.fichier_justificatif:
            messages.error(request, "Aucun fichier justificatif disponible")
            return redirect('professeurs:justifications_attente')
        
        if hasattr(presence.fichier_justificatif, 'tobytes'):
            fichier_bytes = presence.fichier_justificatif.tobytes()
        elif isinstance(presence.fichier_justificatif, bytes):
            fichier_bytes = presence.fichier_justificatif
        elif isinstance(presence.fichier_justificatif, memoryview):
            fichier_bytes = presence.fichier_justificatif.tobytes()
        else:
            fichier_bytes = bytes(presence.fichier_justificatif)
        
        fichier_type = detecter_type_fichier(fichier_bytes)
        
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
            
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Presence.DoesNotExist:
        messages.error(request, "Fichier non trouvé ou vous n'êtes pas autorisé")
        return redirect('professeurs:justifications_attente')
    except Exception as e:
        print(f"Erreur dans telecharger_fichier_justificatif: {e}")
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect('professeurs:justifications_attente')

# =========================================
# Afficher fichier dans un nouvel onglet
# =========================================
def afficher_fichier(request, presence_id):
    """
    Afficher un fichier dans un nouvel onglet
    """
    if 'professeur_id' not in request.session:
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur, Presence
        prof = Professeur.objects.get(utilisateur_id=request.session['professeur_id'])
        
        presence = Presence.objects.get(
            id=presence_id,
            seance__cours__professeur=prof
        )
        
        if not presence.fichier_justificatif:
            messages.error(request, "Aucun fichier justificatif disponible")
            return redirect('professeurs:justifications_attente')
        
        if hasattr(presence.fichier_justificatif, 'tobytes'):
            fichier_bytes = presence.fichier_justificatif.tobytes()
        elif isinstance(presence.fichier_justificatif, bytes):
            fichier_bytes = presence.fichier_justificatif
        elif isinstance(presence.fichier_justificatif, memoryview):
            fichier_bytes = presence.fichier_justificatif.tobytes()
        else:
            fichier_bytes = bytes(presence.fichier_justificatif)
        
        fichier_type = detecter_type_fichier(fichier_bytes)
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
                    <iframe src="data:application/pdf;base64,{fichier_base64}"></iframe>
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
                        <img src="data:{fichier_type};base64,{fichier_base64}" 
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

# =========================================
# Justifications en attente
# =========================================
def justifications_attente(request):
    """
    Affiche toutes les justifications en attente de validation
    """
    if 'professeur_id' not in request.session:
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur, Presence
        
        prof = Professeur.objects.get(utilisateur_id=request.session['professeur_id'])
        
        statut_filter = request.GET.get('statut', 'EN_ATTENTE')
        
        queryset = Presence.objects.filter(
            seance__cours__professeur=prof,
            statut='ABSENT_JUSTIFIE'
        ).select_related(
            'etudiant__utilisateur',
            'seance__cours',
            'seance__groupe'
        ).order_by('-date_saisie')
        
        if statut_filter == 'ACCEPTEE':
            justifications = queryset.filter(statut_justification='ACCEPTEE')
            titre = "Justifications acceptées"
        elif statut_filter == 'REFUSEE':
            justifications = queryset.filter(statut_justification='REFUSEE')
            titre = "Justifications refusées"
        elif statut_filter == 'TRAITEES':
            justifications = queryset.filter(
                statut_justification__in=['ACCEPTEE', 'REFUSEE']
            )
            titre = "Justifications traitées"
        elif statut_filter == 'TOUS':
            justifications = queryset
            titre = "Toutes les justifications"
        else:
            justifications = queryset.filter(statut_justification='EN_ATTENTE')
            titre = "Justifications en attente"
        
        justifications_list = []
        for presence in justifications:
            item = {
                'presence': presence,
                'has_file': bool(presence.fichier_justificatif)
            }
            justifications_list.append(item)
        
        total_en_attente = Presence.objects.filter(
            seance__cours__professeur=prof,
            statut='ABSENT_JUSTIFIE',
            statut_justification='EN_ATTENTE'
        ).count()
        
        total_traitees = Presence.objects.filter(
            seance__cours__professeur=prof,
            statut='ABSENT_JUSTIFIE',
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
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect("professeurs:dashboard_professeur")

# =========================================
# Voir justification
# =========================================
def voir_justification(request, presence_id):
    """
    Voir les détails d'une justification
    """
    if 'professeur_id' not in request.session:
        return redirect("professeurs:login_view")
    
    try:
        from Home.models import Professeur, Presence
        
        prof = Professeur.objects.get(utilisateur_id=request.session['professeur_id'])
        
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
            fichier_base64 = base64.b64encode(presence.fichier_justificatif).decode('utf-8')
            fichier_type = detecter_type_fichier(presence.fichier_justificatif)
            
            fichier_justificatif = {
                'data': fichier_base64,
                'type': fichier_type,
                'has_file': True
            }
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

# =========================================
# Traiter une justification
# =========================================
def traiter_justification(request, presence_id):
    """
    Traiter une justification (accepter ou refuser)
    """
    if 'professeur_id' not in request.session:
        return redirect("professeurs:login_view")
    
    if request.method == 'POST':
        try:
            from Home.models import Professeur, Presence
            
            prof = Professeur.objects.get(utilisateur_id=request.session['professeur_id'])
            
            presence = Presence.objects.get(
                id=presence_id,
                seance__cours__professeur=prof,
                statut='ABSENT_JUSTIFIE'
            )
            
            action = request.POST.get('action')
            commentaire_prof = request.POST.get('commentaire_prof', '').strip()
            
            if action == 'accepter':
                presence.statut_justification = 'ACCEPTEE'
                message = f"La justification de {presence.etudiant.utilisateur.prenom} {presence.etudiant.utilisateur.nom} a été acceptée."
                message_type = 'success'
            elif action == 'refuser':
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

# =========================================
# Afficher fichier dans modal (SANS BOUTON "OUVRIR")
# =========================================
def afficher_fichier_modal(request, presence_id):
    """
    Afficher un fichier dans une modal
    """
    if 'professeur_id' not in request.session:
        return HttpResponse("Non autorisé", status=401)
    
    try:
        from Home.models import Professeur, Presence
        prof = Professeur.objects.get(utilisateur_id=request.session['professeur_id'])
        
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
            if hasattr(presence.fichier_justificatif, 'tobytes'):
                fichier_bytes = presence.fichier_justificatif.tobytes()
            elif isinstance(presence.fichier_justificatif, bytes):
                fichier_bytes = presence.fichier_justificatif
            elif isinstance(presence.fichier_justificatif, memoryview):
                fichier_bytes = presence.fichier_justificatif.tobytes()
            else:
                fichier_bytes = bytes(presence.fichier_justificatif)
            
            fichier_base64 = base64.b64encode(fichier_bytes).decode('utf-8')
            fichier_type = detecter_type_fichier(fichier_bytes)
            
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
        
        if fichier_type.startswith('image/'):
            html_content = f'''
            <div class="text-center">
                <img src="data:{fichier_type};base64,{fichier_base64}" 
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
                        src="data:application/pdf;base64,{fichier_base64}" 
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
    
    #seances
def mes_seances(request):
    """Page des séances avec filtrage"""
    professeur_id = request.session.get("professeur_id")
    if not professeur_id:
        return redirect("professeurs:login_view")
    
    try:
        # AJOUTEZ CET IMPORT AU DÉBUT DE LA FONCTION
        from Home.models import Professeur, Seance, Cours, Groupe, Presence
        from datetime import timedelta  # IMPORT AJOUTÉ
        
        # Récupérer le professeur
        prof = Professeur.objects.get(utilisateur_id=professeur_id)
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
        
        # Obtenir les séances finales (évaluer la requête)
        seances = seances_query.select_related('cours', 'groupe').order_by('-date', 'heure_debut')
        
        # CORRECTION ICI: Utiliser 'seances__cours__professeur' au lieu de 'seance__cours__professeur'
        tous_groupes = Groupe.objects.filter(
            seances__cours__professeur=prof  # CHANGÉ: seances (pluriel) au lieu de seance
        ).distinct().order_by('nom')
        
        # Statistiques globales (sans filtres)
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
        
        # Vérifier si des présences existent pour chaque séance
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
        
    except Professeur.DoesNotExist:
        request.session.flush()
        messages.error(request, "Professeur non trouvé")
        return redirect("professeurs:login_view")
    except Exception as e:
        print(f"ERROR dans mes_seances: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Version de secours
        try:
            from Home.models import Professeur
            prof = Professeur.objects.get(utilisateur_id=professeur_id)
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
        except Exception as inner_e:
            messages.error(request, f"Erreur: {str(e)}")
            return redirect("professeurs:dashboard_professeur")