from django.shortcuts import render
from services.services import liste_presences_etudiant

def mes_presences(request):
    etudiant_id = request.user.id
    presences = liste_presences_etudiant(etudiant_id)
    return render(request, "etudiants/presences.html", {"presences": presences})
