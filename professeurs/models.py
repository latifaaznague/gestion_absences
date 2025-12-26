from django.db import models
from etudiants.models import Etudiant
from Absenceflow.models import Groupe, Seance, Presence
from datetime import datetime, date

class Professeur(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    groupes = models.ManyToManyField(Groupe)

    # Ici tu peux mettre toutes tes méthodes vues dans le shell
    def voir_liste_etudiants(self, groupe):
        return groupe.etudiant_set.all()
