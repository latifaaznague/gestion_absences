from jsonrpcserver import method, serve
from Absenceflow.models import Professeur, Groupe, Seance, Presence, Planning
from etudiants.models import Etudiant
from django.shortcuts import get_object_or_404
from datetime import date

# -------------------------------
# Méthodes RPC exposées
# -------------------------------

@method
def cours_du_jour_rpc(prof_id: int):
    prof = Professeur.objects.get(id=prof_id)
    seances = prof.voir_cours_du_jour()
    return [{"id": s.id, "date": str(s.date), "groupe": s.groupe.nom, "salle": s.salle} for s in seances]

@method
def marquer_presence_rpc(prof_id: int, groupe_id: int, seance_id: int):
    prof = Professeur.objects.get(id=prof_id)
    groupe = Groupe.objects.get(id=groupe_id)
    seance = Seance.objects.get(id=seance_id)
    prof.marquer_presence(groupe, seance)
    return {"message": "Présences marquées avec succès"}

@method
def statistiques_seance_rpc(seance_id: int):
    seance = Seance.objects.get(id=seance_id)
    prof = seance.professeur
    stats = prof.voir_statistiques(seance)
    return stats

@method
def donnees_graphique_rpc(seance_id: int):
    seance = Seance.objects.get(id=seance_id)
    prof = seance.professeur
    return prof.voir_donnees_graphique(seance)

@method
def taux_presence_moyen_rpc(prof_id: int):
    prof = Professeur.objects.get(id=prof_id)
    taux = prof.voir_taux_presence_moyen()
    return {"taux_moyen": taux}

@method
def liste_etudiants_rpc(groupe_id: int):
    groupe = Groupe.objects.get(id=groupe_id)
    return [{"id": e.id, "nom": e.nom, "prenom": e.prenom, "email": e.email} for e in groupe.etudiant_set.all()]

@method
def historique_etudiant_rpc(etudiant_id: int):
    etudiant = Etudiant.objects.get(id=etudiant_id)
    presences = Presence.objects.filter(etudiant=etudiant)
    return [{"seance": p.seance.id, "date": str(p.seance.date), "statut": p.statut} for p in presences]

@method
def tableau_de_bord_rpc(prof_id: int):
    prof = Professeur.objects.get(id=prof_id)
    return prof.voir_tableau_bord()

@method
def presence_globale_rpc(prof_id: int):
    prof = Professeur.objects.get(id=prof_id)
    presences = prof.voir_presence_globale()
    return [{"etudiant": p.etudiant.nom, "seance": p.seance.id, "statut": p.statut} for p in presences]

# -------------------------------
# Lancement du serveur RPC
# -------------------------------
if __name__ == "__main__":
    print("Starting RPC Server on http://localhost:5000")
    serve("localhost", 5000)
