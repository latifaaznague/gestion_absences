from django.shortcuts import render
from services import rpc_client  

def test_rpc(request):
 
    presences = rpc_client.get_presences(etudiant_id=1)
    return render(request, "test.html", {"data": presences})
