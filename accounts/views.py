from django.shortcuts import render, redirect
from services.rpc_client import JsonRpcClient, RpcError

rpc_client = JsonRpcClient("http://127.0.0.1:8001/rpc")
def login_page(request):
    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        mot_de_passe = request.POST.get("motDePasse", "")

        try:
            # Appel RPC pour la connexion
            res = rpc_client.call("auth.login", {
                "email": email, 
                "motDePasse": mot_de_passe
            })

            if res and "token" in res:
                # Stocker TOUTES les informations dans la session
                request.session["rpc_token"] = res["token"]
                request.session["role"] = res.get("role", "ADMINISTRATEUR")
                
                # IMPORTANT : Stocker l'ID utilisateur
                request.session["user_id"] = res.get("user_id")  # Vérifiez que cette clé existe
                
                # Stocker aussi les informations personnelles
                request.session["user_nom"] = res.get("nom", "Admin")
                request.session["user_prenom"] = res.get("prenom", "Système")
                request.session["user_email"] = res.get("email", "admin@system.local")
                request.session["user_type"] = res.get("type_utilisateur", "ADMINISTRATEUR")
                
                # Sauvegarder la session
                request.session.save()
                
                print(f"[DEBUG Login] Session data after login: {dict(request.session)}")
                print(f"[DEBUG Login] User ID: {res.get('user_id')}")
                
                return redirect("administration:admin_dashboard")
            else:
                error = "Le serveur n'a pas renvoyé de jeton valide."

        except RpcError as e:
            error = str(e)
            print(f"[DEBUG Login] RPC Error: {e}")

    return render(request, "accounts/login.html", {"error": error})

def logout_view(request):
    """Déconnexion"""
    from services.rpc_server import TOKENS
    
    # Supprimer le token RPC
    token = request.session.get("rpc_token")
    if token and token in TOKENS:
        del TOKENS[token]

    # Vider la session Django
    request.session.flush()
    
    # Solution temporaire : redirection directe
    return redirect('/accounts/login/')  # Utilisez une URL directe