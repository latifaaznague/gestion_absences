from django.db import models
from Absenceflow.models import Groupe

class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE)
