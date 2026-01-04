# Home/decorators.py
from django.shortcuts import redirect
from functools import wraps

def auth_required_django(roles=None):
    """Décorateur pour vérifier l'authentification avec notre système de session"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Vérifier si l'utilisateur est connecté dans notre session
            if not request.session.get('logged_in'):
                return redirect('/login/')
            
            # Vérifier les rôles si spécifiés
            if roles:
                user_role = request.session.get('user_role')
                if user_role not in roles:
                    return redirect('/login/')
            
            # Ajouter les infos utilisateur à la requête
            request.user_info = {
                'id': request.session.get('user_id'),
                'role': request.session.get('user_role'),
                'nom': request.session.get('user_nom'),
                'prenom': request.session.get('user_prenom'),
                'email': request.session.get('user_email')
            }
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator