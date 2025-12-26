from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from Absenceflow.models import Professeur, Groupe, Seance, Presence, Planning
from etudiants.models import Etudiant
from datetime import date

# 1️⃣ Voir les cours du jour
def cours_du_jour(request, prof_id):
    prof = get_object_or_404(Professeur, id=prof_id)
    seances = prof.voir_cours_du_jour()
    data = [{"id": s.id, "date": str(s.date), "groupe": s.groupe.nom, "salle": s.salle} for s in seances]
    return JsonResponse({"cours_du_jour": data})

# 2️⃣ Marquer la présence d'un groupe pour une séance
def marquer_presence(request, prof_id, groupe_id, seance_id):
    prof = get_object_or_404(Professeur, id=prof_id)
    groupe = get_object_or_404(Groupe, id=groupe_id)
    seance = get_object_or_404(Seance, id=seance_id)
    prof.marquer_presence(groupe, seance)
    return JsonResponse({"message": "Présences marquées avec succès"})

# 3️⃣ Voir statistiques d'une séance
def statistiques_seance(request, seance_id):
    seance = get_object_or_404(Seance, id=seance_id)
    prof = seance.professeur
    stats = prof.voir_statistiques(seance)
    return JsonResponse(stats)

# 4️⃣ Voir données graphique Présents/Absents
def donnees_graphique(request, seance_id):
    seance = get_object_or_404(Seance, id=seance_id)
    prof = seance.professeur
    data = prof.voir_donnees_graphique(seance)
    return JsonResponse(data)

# 5️⃣ Voir taux de présence moyen
def taux_presence_moyen(request, prof_id):
    prof = get_object_or_404(Professeur, id=prof_id)
    taux = prof.voir_taux_presence_moyen()
    return JsonResponse({"taux_moyen": taux})

# 6️⃣ Voir liste des étudiants d'un groupe
def liste_etudiants(request, groupe_id):
    groupe = get_object_or_404(Groupe, id=groupe_id)
    data = [{"id": e.id, "nom": e.nom, "prenom": e.prenom, "email": e.email} for e in groupe.etudiant_set.all()]
    return JsonResponse({"etudiants": data})

# 7️⃣ Voir historique de présence d’un étudiant
def historique_etudiant(request, etudiant_id):
    etudiant = get_object_or_404(Etudiant, id=etudiant_id)
    presences = Presence.objects.filter(etudiant=etudiant)
    data = [{"seance": p.seance.id, "date": str(p.seance.date), "statut": p.statut} for p in presences]
    return JsonResponse({"historique": data})

# 8️⃣ Voir tableau de bord global du professeur
def tableau_de_bord(request, prof_id):
    prof = get_object_or_404(Professeur, id=prof_id)
    data = prof.voir_tableau_bord()
    return JsonResponse(data)

# 9️⃣ Voir présence globale
def presence_globale(request, prof_id):
    prof = get_object_or_404(Professeur, id=prof_id)
    presences = prof.voir_presence_globale()
    data = [{"etudiant": p.etudiant.nom, "seance": p.seance.id, "statut": p.statut} for p in presences]
    return JsonResponse({"presences": data})
