from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import uuid
from services.rpc_client import login_etudiant
from Home.models import Etudiant, Promotion, Filiere, Groupe, Seance, EtudiantGroupe, Presence, Notification

# =========================================
# FONCTION UTILITAIRE - Comptage des notifications
# =========================================
def get_notifications_count(etudiant_id):
    """
    Retourne le nombre de notifications non lues pour un étudiant
    """
    try:
        etu = Etudiant.objects.get(utilisateur_id=etudiant_id)
        count = Notification.objects.filter(
            etudiant=etu,
            lu=False
        ).count()
        return count
    except Etudiant.DoesNotExist:
        return 0

# =========================================
# CONTEXTE PROCESSOR (optionnel mais recommandé)
# =========================================
def notifications_context(request):
    """
    Context processor pour ajouter notifications_count à tous les templates
    """
    if 'etudiant_id' in request.session:
        count = get_notifications_count(request.session['etudiant_id'])
        return {'notifications_count': count}
    return {'notifications_count': 0}

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

    # Récupérer les IDs des groupes
    groupe_ids = EtudiantGroupe.objects.filter(
        etudiant=etu
    ).values_list('groupe_id', flat=True)
    
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

    # Calculer les statistiques de présence
    total_presences = 0
    presents = 0
    absents_justifies = 0
    absents_non_justifies = 0
    taux_presence = 0
    
    if hasattr(etu, 'presences'):
        total_presences = etu.presences.count()
        if total_presences > 0:
            presents = etu.presences.filter(statut='PRESENT').count()
            absents_justifies = etu.presences.filter(statut='ABSENT_JUSTIFIE').count()
            absents_non_justifies = etu.presences.filter(statut='ABSENT_NON_JUSTIFIE').count()
            taux_presence = round((presents / total_presences * 100), 2)

    # Compter les notifications non lues
    notifications_count = get_notifications_count(etudiant_id)

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
        
        # Absences
        "absences": absences,
        "nombre_absences": len(absences),
        
        # Statistiques de présence
        "stats": {
            "total_seances": total_presences,
            "presents": presents,
            "absents_justifies": absents_justifies,
            "absents_non_justifies": absents_non_justifies,
            "total_absences": absents_justifies + absents_non_justifies,
            "taux_presence": taux_presence
        },
        
        # Notifications
        "notifications_count": notifications_count
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
# Vue des présences/absences
# =========================================
def mes_presences(request):
    """
    Affiche les présences et absences de l'étudiant
    """
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")

    try:
        etu = Etudiant.objects.get(utilisateur_id=etudiant_id)
    except Etudiant.DoesNotExist:
        request.session.flush()
        return redirect("etudiants:login_view")

    # Récupérer le filtre si présent
    statut_filter = request.GET.get('statut', 'TOUS')
    
    # Récupérer toutes les présences avec filtre
    presences = []
    if hasattr(etu, 'presences'):
        presences_query = etu.presences.all()
        
        if statut_filter != 'TOUS':
            presences_query = presences_query.filter(statut=statut_filter)
        
        presences = presences_query.select_related(
            'seance__cours',
            'seance__groupe'
        ).order_by('-seance__date')

    # Calculer les statistiques
    total = presences.count()
    presents = presences.filter(statut='PRESENT').count()
    absents_justifies = presences.filter(statut='ABSENT_JUSTIFIE').count()
    absents_non_justifies = presences.filter(statut='ABSENT_NON_JUSTIFIE').count()
    taux_presence = round((presents / total * 100), 2) if total > 0 else 0

    # Récupérer les messages d'alerte/succès de la session
    alert = request.session.pop('alert', None)
    success = request.session.pop('success', None)

    # Compter les notifications non lues
    notifications_count = get_notifications_count(etudiant_id)

    context = {
        "etu": etu,
        "utilisateur": etu.utilisateur,
        "presences": presences,
        "total": total,
        "presents": presents,
        "absents_justifies": absents_justifies,
        "absents_non_justifies": absents_non_justifies,
        "taux_presence": taux_presence,
        "statut_filter": statut_filter,
        "today": timezone.now().date(),
        "alert": alert,
        "success": success,
        "notifications_count": notifications_count
    }

    return render(request, "etudiants/mes_presences.html", context)

# =========================================
# Vue pour ajouter une justification
# =========================================
def ajouter_justification(request, presence_id):
    """
    Ajoute une justification à une absence et redirige vers la même page
    """
    if request.method != "POST":
        request.session['alert'] = "Méthode non autorisée"
        return redirect("etudiants:mes_presences")
    
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")
    
    try:
        # Vérifier que l'étudiant existe
        etu = Etudiant.objects.get(utilisateur_id=etudiant_id)
        
        # Vérifier que la présence appartient à l'étudiant
        presence = get_object_or_404(Presence, id=presence_id, etudiant=etu)
        
        # Vérifier que c'est une absence non justifiée
        if presence.statut != 'ABSENT_NON_JUSTIFIE':
            request.session['alert'] = "Cette absence ne peut pas être justifiée"
            return redirect("etudiants:mes_presences")
        
        # MODIFICATION IMPORTANTE : Ne vérifier que si une vraie justification existe
        # (texte non vide ou fichier), pas le statut_justification
        has_text_justification = bool(presence.justification and presence.justification.strip())
        has_file_justification = bool(presence.fichier_justificatif)
        
        if has_text_justification or has_file_justification:
            request.session['alert'] = "Une justification existe déjà pour cette absence"
            return redirect("etudiants:mes_presences")
        
        # Récupérer la justification du formulaire
        justification_text = request.POST.get('justification', '').strip()
        fichier = request.FILES.get('fichier_justificatif', None)
        
        if not justification_text and not fichier:
            request.session['alert'] = "Veuillez fournir une justification ou un fichier"
            return redirect("etudiants:mes_presences")
        
        # Mettre à jour la présence
        if justification_text:
            presence.justification = justification_text
        
        # Sauvegarder le fichier si présent
        if fichier:
            # Vérifier la taille (5MB max)
            if fichier.size > 5 * 1024 * 1024:
                request.session['alert'] = "Le fichier dépasse la taille maximale de 5MB"
                return redirect("etudiants:mes_presences")
            
            # Vérifier le type de fichier
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
            file_ext = os.path.splitext(fichier.name)[1].lower()
            if file_ext not in allowed_extensions:
                request.session['alert'] = "Format de fichier non accepté. Formats acceptés: PDF, JPG, PNG, DOC"
                return redirect("etudiants:mes_presences")
            
            # Lire le contenu du fichier et le stocker dans le BinaryField
            fichier_content = fichier.read()
            presence.fichier_justificatif = fichier_content
        
        # Mettre à jour le statut (le statut_justification reste 'EN_ATTENTE' par défaut)
        presence.statut = 'ABSENT_JUSTIFIE'
        
        # Sauvegarder
        presence.save()
        
        request.session['success'] = "Justification soumise avec succès. Elle sera examinée par le professeur."
        return redirect("etudiants:mes_presences")
        
    except Exception as e:
        request.session['alert'] = f"Erreur: {str(e)}"
        return redirect("etudiants:mes_presences")

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
    
    # Récupérer toutes les justifications avec détails
    justifications = Presence.objects.filter(
        etudiant=etu,
        statut='ABSENT_JUSTIFIE',
        justification__isnull=False
    ).select_related(
        'seance__cours'
    ).order_by('-date_saisie')
    
    # Récupérer aussi les notifications existantes
    notifications = Notification.objects.filter(
        etudiant=etu
    ).select_related(
        'presence__seance__cours'
    ).order_by('-date_envoi')
    
    # Marquer les notifications non lues comme lues
    notifications_non_lues = notifications.filter(lu=False)
    if notifications_non_lues.exists():
        notifications_non_lues.update(lu=True)
        # Mettre à jour le compteur dans la session
        request.session['notifications_count'] = 0
    
    # Compter les notifications non lues
    notifications_count = Notification.objects.filter(
        etudiant=etu,
        lu=False
    ).count()
    
    context = {
        "etu": etu,
        "utilisateur": etu.utilisateur,
        "justifications": justifications,
        "notifications": notifications,
        "notifications_count": notifications_count,
        "today": timezone.now().date(),
    }
    
    return render(request, "etudiants/mes_notifications.html", context)

# =========================================
# Vue pour créer automatiquement des notifications
# =========================================
def creer_notifications_pour_justifications(request):
    """
    Fonction à appeler pour créer des notifications pour toutes les justifications traitées
    """
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return redirect("etudiants:login_view")

    try:
        etu = Etudiant.objects.get(utilisateur_id=etudiant_id)
    except Etudiant.DoesNotExist:
        request.session.flush()
        return redirect("etudiants:login_view")
    
    # Récupérer toutes les justifications traitées sans notification
    justifications = Presence.objects.filter(
        etudiant=etu,
        statut='ABSENT_JUSTIFIE',
        justification__isnull=False,
        statut_justification__in=['ACCEPTEE', 'REFUSEE']
    ).exclude(
        notifications__isnull=False
    ).select_related('seance__cours')
    
    notifications_crees = 0
    
    for justification in justifications:
        # Construire le message de notification
        date_cours = justification.seance.date.strftime("%d/%m/%Y")
        cours = justification.seance.cours.libelle
        
        if justification.statut_justification == 'ACCEPTEE':
            message = f"✅ Votre justification pour le cours '{cours}' du {date_cours} a été acceptée."
        else:  # REFUSEE
            message = f"❌ Votre justification pour le cours '{cours}' du {date_cours} a été refusée."
        
        if justification.feedback_professeur:
            message += f" Feedback : {justification.feedback_professeur}"
        
        # Créer la notification
        Notification.objects.create(
            etudiant=etu,
            presence=justification,
            message=message,
            lu=False
        )
        
        notifications_crees += 1
    
    # Stocker le message dans la session
    if notifications_crees > 0:
        request.session['success'] = f"{notifications_crees} nouvelle(s) notification(s) créée(s)."
    else:
        request.session['info'] = "Aucune nouvelle notification à créer."
    
    return redirect("etudiants:mes_notifications")

# =========================================
# API pour récupérer le nombre de notifications
# (pour rafraîchir sans recharger la page)
# =========================================
def get_notifications_count_api(request):
    """
    API qui retourne le nombre de notifications non lues en JSON
    """
    etudiant_id = request.session.get("etudiant_id")
    if not etudiant_id:
        return JsonResponse({'count': 0})
    
    try:
        count = get_notifications_count(etudiant_id)
        return JsonResponse({'count': count})
    except Exception as e:
        return JsonResponse({'count': 0, 'error': str(e)})