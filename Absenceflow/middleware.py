# Absenceflow/middleware.py
import json
from django.shortcuts import redirect
from django.urls import reverse
# Absenceflow/middleware.py
class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Chemins publics (sans authentification)
        public_paths = [
            '/',  # La racine DOIT être publique
            '/login/', 
            '/api/login/', 
            '/api/check-session/',
            '/api/logout/',
            '/logout/', 
            '/admin/', 
            '/admin/login/',
            '/static/',
            '/media/',
        ]
        
        # DEBUG: Afficher les infos
        print(f"\n=== MIDDLEWARE DEBUG ===")
        print(f"Path: {request.path}")
        print(f"Session logged_in: {request.session.get('logged_in')}")
        print(f"Session user_role: {request.session.get('user_role')}")
        print(f"Is public path: {any(request.path.startswith(path) for path in public_paths)}")
        print("=======================\n")
        
        # Ne pas vérifier l'authentification pour les chemins publics
        if any(request.path.startswith(path) for path in public_paths):
            return self.get_response(request)
        
        # Vérifier si l'utilisateur est connecté via SESSION Django personnalisée
        if not request.session.get('logged_in'):
            print("Middleware: Utilisateur non connecté, redirection vers /login/")
            return redirect('/login/')
        
        # Récupérer le rôle de l'utilisateur
        user_role = request.session.get('user_role', '').upper()
        
        # Vérifier l'accès selon le rôle
        if not self.has_access(request.path, user_role):
            print(f"Middleware: Accès refusé pour {user_role} à {request.path}")
            return redirect('/login/')
        
        return self.get_response(request)
    
    def has_access(self, path, role):
        """Vérifie si l'utilisateur a accès à ce chemin selon son rôle"""
        # Chemins autorisés par rôle
        allowed_paths = {
            'ADMINISTRATEUR': ['/administration/', '/api/', '/admin/'],
            'PROFESSEUR': ['/professeurs/', '/api/'],
            'ETUDIANT': ['/etudiants/', '/api/'],
        }
        
        # Si pas de rôle, autoriser l'accès (le login gérera la redirection)
        if not role or role not in allowed_paths:
            return True
        
        # Vérifier si le chemin est autorisé pour ce rôle
        return any(path.startswith(allowed_path) for allowed_path in allowed_paths.get(role, []))


class DebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        print(f"\n=== DEBUG MIDDLEWARE ===")
        print(f"Path: {request.path}")
        print(f"Session: {dict(request.session)}")
        print(f"Logged in: {request.session.get('logged_in')}")
        print(f"User role: {request.session.get('user_role')}")
        print("=======================\n")
        
        response = self.get_response(request)
        return response