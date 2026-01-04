# debug_utils.py
"""
Décorateurs de débogage pour Django
"""

from functools import wraps

def debug_session(view_func):
    """
    Décorateur pour afficher les informations de session avant d'exécuter une vue.
    
    Exemple d'utilisation :
    
    @auth_required_django(roles=["ADMINISTRATEUR"])
    @debug_session
    def (request):
        # ... votre code
    """
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(f"\n{'='*60}")
        print(f"[DEBUG SESSION] Vue appelée : {view_func.__name__}")
        print(f"[DEBUG SESSION] URL : {request.path}")
        
        # Vérifier si la session existe
        if hasattr(request, 'session'):
            print(f"[DEBUG SESSION] Session disponible : OUI")
            
            # Afficher toutes les clés de session
            session_keys = list(request.session.keys())
            print(f"[DEBUG SESSION] Clés de session ({len(session_keys)}): {session_keys}")
            
            # Afficher les valeurs importantes
            important_keys = ['user_id', 'user_nom', 'user_prenom', 'user_email', 'role', 'rpc_token']
            for key in important_keys:
                value = request.session.get(key)
                print(f"[DEBUG SESSION] {key}: {value}")
            
            # Afficher toutes les valeurs (optionnel)
            print(f"[DEBUG SESSION] Toutes les valeurs :")
            for key in session_keys:
                value = request.session.get(key)
                print(f"  - {key}: {value}")
        else:
            print(f"[DEBUG SESSION] Session disponible : NON")
            print(f"[DEBUG SESSION] ERREUR: L'objet request n'a pas d'attribut 'session'")
        
        print(f"{'='*60}\n")
        
        # Exécuter la vue originale
        return view_func(request, *args, **kwargs)
    
    return wrapper


def debug_request(view_func):
    """
    Décorateur pour afficher les informations de la requête HTTP.
    """
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(f"\n{'='*60}")
        print(f"[DEBUG REQUEST] Vue : {view_func.__name__}")
        print(f"[DEBUG REQUEST] Méthode : {request.method}")
        print(f"[DEBUG REQUEST] URL complète : {request.build_absolute_uri()}")
        print(f"[DEBUG REQUEST] GET params : {dict(request.GET)}")
        
        if request.method == 'POST':
            print(f"[DEBUG REQUEST] POST data :")
            for key, value in request.POST.items():
                print(f"  - {key}: {value}")
        
        print(f"{'='*60}\n")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def debug_rpc(view_func):
    """
    Décorateur pour déboguer les appels RPC.
    """
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(f"\n[DEBUG RPC] Vue : {view_func.__name__}")
        
        # Exécuter la vue
        response = view_func(request, *args, **kwargs)
        
        print(f"[DEBUG RPC] Vue exécutée avec succès\n")
        
        return response
    
    return wrapper


# Fonction utilitaire pour tester la session manuellement
def test_session(request):
    """
    Fonction pour tester manuellement la session depuis le shell.
    """
    if hasattr(request, 'session'):
        print("✓ Session disponible")
        return dict(request.session)
    else:
        print("✗ Session NON disponible")
        return None