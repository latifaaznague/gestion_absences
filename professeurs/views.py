from django.shortcuts import render
from services.services import marquer_presence_etudiant, valider_seance_par_prof

def marquer_presence_view(request):
    if request.method == "POST":
        etudiant_id = int(request.POST.get("etudiant_id"))
        seance_id = int(request.POST.get("seance_id"))
        statut = request.POST.get("statut")
        result = marquer_presence_etudiant(etudiant_id, seance_id, statut)
        return render(request, "professeurs/result.html", {"result": result})
    return render(request, "professeurs/marquer.html")
 