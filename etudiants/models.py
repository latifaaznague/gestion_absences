# etudiants/models.py
from django.db import models


class Promotion(models.Model):
    libelle = models.CharField(max_length=100)
    anneeScolaire = models.CharField(max_length=20)
