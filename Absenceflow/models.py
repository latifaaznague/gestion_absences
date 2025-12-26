from django.db import models
from datetime import date

class Groupe(models.Model):
    nom = models.CharField(max_length=100)

class Seance(models.Model):
    date = models.DateField()
    heure_debut = models.TimeField(null=True)
    heure_fin = models.TimeField(null=True)
    salle = models.CharField(max_length=50)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE)

class Presence(models.Model):
    STATUT_CHOICES = [
        ("PRESENT", "Présent"),
        ("ABSENT_NON_JUSTIFIE", "Absent non justifié"),
        ("ABSENT_JUSTIFIE", "Absent justifié"),
    ]
    statut = models.CharField(max_length=25, choices=STATUT_CHOICES)
    etudiant = models.ForeignKey("etudiants.Etudiant", on_delete=models.CASCADE)
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE)
