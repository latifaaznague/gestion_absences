# Absenceflow/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import connection
# Absenceflow/views.py
def login_view(request):
    """Afficher la page de login UNIQUEMENT si non connecté"""
    print(f"DEBUG login_view - Session: {dict(request.session)}")
    print(f"DEBUG login_view - logged_in: {request.session.get('logged_in')}")
    
    # FORCER la déconnexion pour debug - AJOUTEZ CETTE LIGNE TEMPORAIREMENT
    # request.session.flush()  # Décommentez pour forcer la déconnexion
    
    if request.session.get('logged_in'):
        role = request.session.get('user_role')
        print(f"DEBUG login_view - Déjà connecté en tant que: {role}")
        redirect_url = get_redirect_url(role)
        print(f"DEBUG login_view - Redirection vers: {redirect_url}")
        return redirect(redirect_url)
    
    print("DEBUG login_view - Affichage de la page de login")
    return render(request, 'login.html')
@csrf_exempt
def api_login(request):
    """API pour vérifier les identifiants"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('motDePasse')
            
            print(f"DEBUG api_login - Tentative de connexion pour: {email}")
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, type_utilisateur, nom, prenom, email, mot_de_passe
                    FROM utilisateur 
                    WHERE email = %s
                """, [email])
                
                user = cursor.fetchone()
                
                if not user:
                    print(f"DEBUG api_login - Utilisateur non trouvé")
                    return JsonResponse({
                        'success': False,
                        'message': 'Email ou mot de passe incorrect'
                    })
                
                user_id, role, nom, prenom, user_email, db_password = user
                print(f"DEBUG api_login - Utilisateur trouvé: {nom} {prenom}, rôle: {role}")
                
                if password != db_password:
                    print(f"DEBUG api_login - Mot de passe incorrect")
                    return JsonResponse({
                        'success': False,
                        'message': 'Email ou mot de passe incorrect'
                    })
                
                request.session['logged_in'] = True
                request.session['user_id'] = user_id
                request.session['user_role'] = role
                request.session['user_nom'] = nom
                request.session['user_prenom'] = prenom
                request.session['user_email'] = user_email
                
                request.session.save()
                
                print(f"DEBUG api_login - Session sauvegardée: {dict(request.session)}")
                
                redirect_url = get_redirect_url(role)
                print(f"DEBUG api_login - Redirection vers: {redirect_url}")
                
                return JsonResponse({
                    'success': True,
                    'redirect': redirect_url,
                    'user': {
                        'id': user_id,
                        'role': role,
                        'nom': nom,
                        'prenom': prenom
                    }
                })
                
        except Exception as e:
            print(f"DEBUG api_login - Erreur: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

def logout_view(request):
    """Déconnexion via API"""
    print(f"DEBUG logout_view - Déconnexion, ancienne session: {dict(request.session)}")
    
    request.session.flush()
    
    return JsonResponse({'success': True})

def simple_logout_view(request):
    """Vue simple pour la déconnexion (pour les templates)"""
    print(f"DEBUG simple_logout_view - Déconnexion")
    request.session.flush()
    return redirect('/login/')

def check_session(request):
    """Vérifier si l'utilisateur est connecté"""
    logged_in = request.session.get('logged_in', False)
    print(f"DEBUG check_session - logged_in: {logged_in}")
    
    if logged_in:
        return JsonResponse({
            'logged_in': True,
            'role': request.session.get('user_role'),
            'user': {
                'nom': request.session.get('user_nom'),
                'prenom': request.session.get('user_prenom'),
                'email': request.session.get('user_email')
            }
        })
    else:
        return JsonResponse({'logged_in': False})

def get_redirect_url(role):
    """Retourne l'URL selon le type d'utilisateur"""
    role = (role or '').upper()
    
    if role == 'ADMINISTRATEUR':
        return '/administration/'
    elif role == 'PROFESSEUR':
        return '/professeurs/dashboard/'
    elif role == 'ETUDIANT':
        return '/etudiants/dashboard/'
    else:
        return '/login/'
    

# Absenceflow/views.py - assurez-vous d'avoir cette fonction
def simple_logout_view(request):
    """Vue simple pour la déconnexion (pour les templates)"""
    print(f"DEBUG simple_logout_view - Déconnexion")
    request.session.flush()
    return redirect('/login/')