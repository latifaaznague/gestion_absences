# professeurs/models.py
from django.db import models
from datetime import date, datetime
from etudiants.models import Etudiant
from Absenceflow.model import Presence, Seance, Groupe, Planning


class Professeur(models.Model):
    nom = models.CharField(max_length=100, null=True, blank=True)
    prenom = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, null=True, blank=True)
    matiere = models.CharField(max_length=100, null=True, blank=True)
    groupes = models.ManyToManyField(Groupe, related_name="professeurs", blank=True)
    planning = models.ForeignKey(Planning, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"{self.prenom} {self.nom}"

    # 1) Voir les cours du jour
    def voir_cours_du_jour(self, planning: Planning):
        today = date.today()
        return planning.seances.filter(date=today)

    # 2) Marquer la présence
    def marquer_presence(self, groupe: Groupe, seance: Seance):
        for etu in groupe.etudiants.all():

            Presence.objects.create(
                statut="PRESENT",
                justification=None,
                fichier_justificatif=None,
                date_saisie=datetime.now(),
                etudiant=etu,
                seance=seance
            )

    # 3) Voir les statistiques d'une séance
    def voir_statistiques(self, seance: Seance):

        presences = seance.presence_set.all()
        total = presences.count()

        presents = presences.filter(statut="PRESENT").count()
        absents = presences.filter(statut="ABSENT_NON_JUSTIFIE").count()
        justifies = presences.filter(statut="ABSENT_JUSTIFIE").count()

        return {
            "taux_presence": (presents / total * 100) if total else 0,
            "taux_absence": (absents / total * 100) if total else 0,
            "taux_absence_justifiee": (justifies / total * 100) if total else 0,
        }

    # 4) Voir la liste des étudiants d’un groupe
    def voir_liste_etudiants(self, groupe: Groupe):
        return groupe.etudiants.all()

    # 5) Voir historique d’un étudiant
    def voir_historique_presence(self, etudiant: Etudiant):
        return etudiant.presence_set.all()
