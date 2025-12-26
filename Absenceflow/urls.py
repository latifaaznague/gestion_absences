from django.urls import path
from jsonrpc import jsonrpc_site
from professeurs.rpc import ProfesseurRPCMethods  # on va créer ce fichier

urlpatterns = [
    path("rpc/", jsonrpc_site.dispatch, name="jsonrpc_mountpoint"),
]
