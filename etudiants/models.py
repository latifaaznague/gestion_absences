# etudiants/models.py
from django.db import models
from Absenceflow.model import Groupe

class Promotion(models.Model):
    libelle = models.CharField(max_length=100)
    anneeScolaire = models.CharField(max_length=20)




class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, null=True, blank=True)


    def __str__(self):
        return f"{self.prenom} {self.nom}"
