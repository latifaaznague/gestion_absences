from django.shortcuts import render, redirect
from django.utils import timezone
from services.rpc_client import login_etudiant
from Home.models import Etudiant, Promotion, Filiere, Groupe, Seance, EtudiantGroupe

# =========================================
# Login étudiant
# =========================================
def login_view(request):
    """
    Gère la connexion des étudiants
    """
    if request.method == "POST":
        email = request.POST.get("email")
        mot_de_passe = request.POST.get("mot_de_passe")

        try:
            # Appel au serveur RPC
            result = login_etudiant(email, mot_de_passe)
        except Exception as e:
            # Erreur réseau ou serveur RPC
            return render(request, "etudiants/login.html", {
                "alert": f"Erreur de connexion au serveur : {str(e)}"
            })

        if result.get("status") == "success":
            # Connexion réussie - stocker en session
            request.session["etudiant_id"] = result["etudiant_id"]
            request.session["nom"] = result["nom"]
            request.session["prenom"] = result["prenom"]
            request.session["code_etudiant"] = result.get("code_etudiant", "")
            
            # Rediriger vers le dashboard
            return redirect("etudiants:dashboard_etudiant")
        else:
            # Connexion échouée
            return render(request, "etudiants/login.html", {
                "alert": result.get("message", "Email ou mot de passe incorrect")
            })

    # GET request - afficher le formulaire
    return render(request, "etudiants/login.html")


# =========================================
# Dashboard étudiant
# =========================================
def dashboard_etudiant(request):
    """
    Affiche le tableau de bord de l'étudiant
    """
    # Vérifier si l'étudiant est connecté
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")

    try:
        # Récupérer l'étudiant avec ses relations
        etu = Etudiant.objects.select_related(
            'utilisateur',          # Informations utilisateur
            'promotion',            # Promotion de l'étudiant
            'promotion__filiere'    # Filière de la promotion
        ).get(utilisateur_id=etudiant_id)
        
    except Etudiant.DoesNotExist:
        # Étudiant non trouvé - déconnecter et rediriger
        request.session.flush()
        return redirect("etudiants:login_view")

    # Récupérer les informations
    utilisateur = etu.utilisateur
    promotion = etu.promotion
    filiere = promotion.filiere if promotion else None

    # Récupérer les groupes de l'étudiant via la table d'association
    # CORRECTION: Utiliser EtudiantGroupe car il n'y a pas de relation directe 'groupes'
    etudiant_groupes = EtudiantGroupe.objects.filter(
        etudiant=etu
    ).select_related('groupe')
    
    # Extraire les IDs des groupes
    groupe_ids = [eg.groupe.id for eg in etudiant_groupes]
    
    # Récupérer les objets Groupe
    groupes = Groupe.objects.filter(id__in=groupe_ids).select_related('promotion')

    # Récupérer les séances prévues aujourd'hui
    today = timezone.now().date()
    seances_aujourdhui = Seance.objects.filter(
        groupe__in=groupes,
        date=today
    ).select_related('cours', 'groupe').order_by('heure_debut')

    # Récupérer les absences (pour les notifications)
    absences = []
    if hasattr(etu, 'presences'):
        absences = etu.presences.filter(
            statut__in=['ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE']
        ).select_related('seance__cours').order_by('-seance__date')[:5]

    # Récupérer les notifications non lues
    notifications = []
    if hasattr(etu, 'notifications'):
        notifications = etu.notifications.filter(lu=False).order_by('-date_envoi')[:10]

    # Préparer le contexte
    context = {
        # Informations étudiant
        "etu": etu,
        "utilisateur": utilisateur,
        
        # Informations académiques
        "promotion": promotion,
        "filiere": filiere,
        
        # Groupes et emploi du temps
        "groupes": groupes,
        "seances_aujourdhui": seances_aujourdhui,
        "today": today,
        
        # Statistiques
        "total_seances_aujourdhui": seances_aujourdhui.count(),
        "total_groupes": groupes.count(),
        
        # Absences et notifications
        "absences": absences,
        "notifications": notifications,
        "nombre_notifications_non_lues": len(notifications),
    }

    return render(request, "etudiants/dashboard.html", context)


# =========================================
# Déconnexion
# =========================================
def logout_view(request):
    """
    Déconnecte l'étudiant
    """
    request.session.flush()  # Supprime toutes les données de session
    return redirect("etudiants:login_view")


# =========================================
# Vue des absences
# =========================================
def mes_absences(request):
    """
    Affiche les absences de l'étudiant
    """
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")

    try:
        etu = Etudiant.objects.get(utilisateur_id=etudiant_id)
    except Etudiant.DoesNotExist:
        request.session.flush()
        return redirect("etudiants:login_view")

    # Récupérer toutes les absences
    absences = []
    if hasattr(etu, 'presences'):
        absences = etu.presences.filter(
            statut__in=['ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE']
        ).select_related(
            'seance__cours',
            'seance__groupe'
        ).order_by('-seance__date')

    # Calculer les statistiques
    total_absences = absences.count()
    absences_justifiees = absences.filter(statut='ABSENT_JUSTIFIE').count()
    absences_non_justifiees = absences.filter(statut='ABSENT_NON_JUSTIFIE').count()

    context = {
        "etu": etu,
        "utilisateur": etu.utilisateur,
        "absences": absences,
        "total_absences": total_absences,
        "absences_justifiees": absences_justifiees,
        "absences_non_justifiees": absences_non_justifiees,
    }

    return render(request, "etudiants/mes_absences.html", context)


# =========================================
# Vue des notifications
# =========================================
def mes_notifications(request):
    """
    Affiche les notifications de l'étudiant
    """
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")

    try:
        etu = Etudiant.objects.get(utilisateur_id=etudiant_id)
    except Etudiant.DoesNotExist:
        request.session.flush()
        return redirect("etudiants:login_view")

    # Récupérer toutes les notifications
    notifications = []
    if hasattr(etu, 'notifications'):
        notifications = etu.notifications.all().order_by('-date_envoi')

    # Marquer comme lues si demandé
    if request.method == "POST" and "marquer_comme_lues" in request.POST:
        etu.notifications.filter(lu=False).update(lu=True)
        return redirect("etudiants:mes_notifications")

    context = {
        "etu": etu,
        "utilisateur": etu.utilisateur,
        "notifications": notifications,
        "nombre_notifications": notifications.count(),
        "nombre_non_lues": notifications.filter(lu=False).count(),
    }

    return render(request, "etudiants/mes_notifications.html", context)


# =========================================
# Vue du planning
# =========================================
def mon_planning(request):
    """
    Affiche le planning de l'étudiant
    """
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")

    try:
        etu = Etudiant.objects.get(utilisateur_id=etudiant_id)
    except Etudiant.DoesNotExist:
        request.session.flush()
        return redirect("etudiants:login_view")

    # Récupérer les groupes
    groupe_ids = EtudiantGroupe.objects.filter(
        etudiant=etu
    ).values_list('groupe_id', flat=True)
    
    # Récupérer les séances de la semaine
    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday())  # Lundi
    end_of_week = start_of_week + timezone.timedelta(days=6)  # Dimanche

    seances_semaine = Seance.objects.filter(
        groupe__id__in=groupe_ids,
        date__range=[start_of_week, end_of_week]
    ).select_related('cours', 'groupe').order_by('date', 'heure_debut')

    # Grouper par jour
    planning_par_jour = {}
    for seance in seances_semaine:
        jour = seance.date.strftime("%A %d/%m/%Y")
        if jour not in planning_par_jour:
            planning_par_jour[jour] = []
        planning_par_jour[jour].append(seance)

    context = {
        "etu": etu,
        "utilisateur": etu.utilisateur,
        "seances_semaine": seances_semaine,
        "planning_par_jour": planning_par_jour,
        "start_of_week": start_of_week,
        "end_of_week": end_of_week,
        "today": today,
    }

    return render(request, "etudiants/mon_planning.html", context)


# =========================================
# Vue de profil
# =========================================
def mon_profil(request):
    """
    Affiche le profil de l'étudiant
    """
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")

    try:
        etu = Etudiant.objects.select_related(
            'utilisateur',
            'promotion__filiere'
        ).get(utilisateur_id=etudiant_id)
    except Etudiant.DoesNotExist:
        request.session.flush()
        return redirect("etudiants:login_view")

    # Récupérer les statistiques
    total_presences = 0
    taux_presence = 0
    
    if hasattr(etu, 'presences'):
        total_seances = etu.presences.count()
        if total_seances > 0:
            presences = etu.presences.filter(statut='PRESENT').count()
            total_presences = presences
            taux_presence = round((presences / total_seances) * 100, 2)

    context = {
        "etu": etu,
        "utilisateur": etu.utilisateur,
        "promotion": etu.promotion,
        "filiere": etu.promotion.filiere if etu.promotion else None,
        "total_presences": total_presences,
        "taux_presence": taux_presence,
    }

    return render(request, "etudiants/mon_profil.html", context)