# Absenceflow/model.py

from django.db import models
from datetime import date


# --------------------------------------------------------
# 1) GROUPE D'ÉTUDIANTS
# --------------------------------------------------------

class Groupe(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self):
        return self.nom


# --------------------------------------------------------
# 2) SÉANCE DE COURS
# --------------------------------------------------------

class Seance(models.Model):
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    salle = models.CharField(max_length=50)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, related_name="seances")

    def __str__(self):
        return f"Séance {self.date} - {self.groupe.nom} ({self.salle})"


# --------------------------------------------------------
# 3) PRESENCE
# --------------------------------------------------------

class Presence(models.Model):

    STATUT_CHOICES = [
        ("PRESENT", "Présent"),
        ("ABSENT_NON_JUSTIFIE", "Absent non justifié"),
        ("ABSENT_JUSTIFIE", "Absent justifié"),
    ]

    statut = models.CharField(max_length=25, choices=STATUT_CHOICES)
    justification = models.TextField(null=True, blank=True)
    fichier_justificatif = models.FileField(upload_to="justificatifs/", null=True, blank=True)
    date_saisie = models.DateTimeField(auto_now_add=True)

    etudiant = models.ForeignKey(
        "etudiants.Etudiant",
        on_delete=models.CASCADE,
        related_name="presences"
    )
    seance = models.ForeignKey(
        Seance,
        on_delete=models.CASCADE,
        related_name="presences"
    )

    def __str__(self):
        return f"{self.etudiant.nom} - {self.seance.date} ({self.statut})"


# --------------------------------------------------------
# 4) PLANNING (liste de séances)
# --------------------------------------------------------

class Planning(models.Model):
    nom = models.CharField(max_length=100)
    seances = models.ManyToManyField(Seance, related_name="plannings")

    def get_seances_du_jour(self, day: date):
        return self.seances.filter(date=day)

    def __str__(self):
        return self.nom
