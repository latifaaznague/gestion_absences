from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import uuid
from services.rpc_client import login_etudiant
from Home.models import Etudiant, Promotion, Filiere, Groupe, Seance, EtudiantGroupe, Presence

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
        }
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
        "success": success
    }

    return render(request, "etudiants/mes_presences.html", context)


# =========================================
# Vue pour ajouter une justification (CORRIGÉE)
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

    # Pour le moment, retourner une page vide
    context = {
        "etu": etu,
        "utilisateur": etu.utilisateur,
    }

    return render(request, "etudiants/mes_notifications.html", context)