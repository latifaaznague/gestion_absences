# Home/management/commands/sync_notifications_existantes.py
from django.core.management.base import BaseCommand
from Home.models import Presence, Notification
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronise les notifications pour les données existantes'

    def handle(self, *args, **options):
        self.stdout.write("=== Synchronisation des notifications existantes ===")
        
        # MODIFIÉ: Ne pas utiliser notification_absence_cree qui n'existe pas encore
        # 1. Notifications pour TOUTES les absences existantes
        toutes_absences = Presence.objects.filter(
            statut__in=['ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE']
        )
        
        self.stdout.write(f"Total absences: {toutes_absences.count()}")
        
        compteur_absences = 0
        for absence in toutes_absences:
            try:
                # Vérifier si une notification d'absence existe déjà
                # On vérifie par le message qui contient "absence"
                if Notification.objects.filter(
                    presence=absence,
                    message__icontains="absence"
                ).exists():
                    continue  # Notification existe déjà, on passe
                
                date_cours = absence.seance.date.strftime("%d/%m/%Y")
                cours = absence.seance.cours.libelle
                
                if absence.statut == 'ABSENT_JUSTIFIE':
                    message = f"⚠️ Vous avez une absence justifiée au cours de '{cours}' du {date_cours}."
                else:
                    message = f"❌ Vous avez une absence non justifiée au cours de '{cours}' du {date_cours}."
                
                message += f" Horaire: {absence.seance.heure_debut.strftime('%H:%M')}-{absence.seance.heure_fin.strftime('%H:%M')}"
                
                if absence.seance.salle:
                    message += f" en salle {absence.seance.salle}"
                
                Notification.objects.create(
                    etudiant=absence.etudiant,
                    presence=absence,
                    message=message,
                    lu=False,
                    date_envoi=absence.date_saisie
                )
                
                compteur_absences += 1
                if compteur_absences % 10 == 0:
                    self.stdout.write(f"  {compteur_absences} notifications d'absence créées...")
                
            except Exception as e:
                self.stderr.write(f"  ✗ Erreur pour absence {absence.id}: {str(e)}")
        
        self.stdout.write(f"✓ Notifications d'absence créées: {compteur_absences}")
        
        # 2. Notifications pour les justifications traitées
        justifications_traitees = Presence.objects.filter(
            statut='ABSENT_JUSTIFIE',
            justification__isnull=False,
            statut_justification__in=['ACCEPTEE', 'REFUSEE']
        )
        
        self.stdout.write(f"\nJustifications traitées: {justifications_traitees.count()}")
        
        compteur_justifications = 0
        for justification in justifications_traitees:
            try:
                # Déterminer le statut
                if justification.statut_justification == 'ACCEPTEE':
                    prefix = "✅"
                    statut_text = "acceptée"
                    search_text = "acceptée"
                else:
                    prefix = "❌"
                    statut_text = "refusée"
                    search_text = "refusée"
                
                # Vérifier si une notification existe déjà
                if Notification.objects.filter(
                    presence=justification,
                    message__icontains=search_text
                ).exists():
                    continue  # Notification existe déjà, on passe
                
                date_cours = justification.seance.date.strftime("%d/%m/%Y")
                cours = justification.seance.cours.libelle
                
                message = f"{prefix} Votre justification pour le cours '{cours}' du {date_cours} a été {statut_text}."
                
                if justification.feedback_professeur:
                    message += f" Feedback du professeur: {justification.feedback_professeur}"
                
                Notification.objects.create(
                    etudiant=justification.etudiant,
                    presence=justification,
                    message=message,
                    lu=False,
                    date_envoi=justification.date_saisie
                )
                
                compteur_justifications += 1
                if compteur_justifications % 10 == 0:
                    self.stdout.write(f"  {compteur_justifications} notifications de justification créées...")
                    
            except Exception as e:
                self.stderr.write(f"  ✗ Erreur pour justification {justification.id}: {str(e)}")
        
        self.stdout.write(f"✓ Notifications de justification créées: {compteur_justifications}")
        
        # 3. Statistiques finales
        total_notifications = Notification.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(f"\n=== SYNCHRONISATION TERMINÉE ===")
        )
        self.stdout.write(f"Total notifications créées: {compteur_absences + compteur_justifications}")
        self.stdout.write(f"Total notifications en base: {total_notifications}")
        self.stdout.write(f"Absences synchronisées: {compteur_absences}")
        self.stdout.write(f"Justifications synchronisées: {compteur_justifications}")