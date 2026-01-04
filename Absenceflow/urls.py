# Absenceflow/urls.py
from django.contrib import admin
from django.urls import path, include
from Absenceflow.views import login_view, api_login, logout_view, check_session, simple_logout_view  # AJOUTEZ simple_logout_view

urlpatterns = [
    # Votre login personnalisé
    path('', login_view, name='home'),
    path('login/', login_view, name='login'),
    
    # Admin Django
    path('admin/', admin.site.urls),
    
    # API pour l'authentification
    path('api/login/', api_login, name='api_login'),
    path('api/logout/', logout_view, name='api_logout'),
    path('api/check-session/', check_session, name='check_session'),
    
    # Vue simple de déconnexion pour les templates
    path('logout/', simple_logout_view, name='logout'),  # <-- AJOUTEZ CETTE LIGNE
    
    # Vos applications
    path('etudiants/', include('etudiants.urls')),
    path('professeurs/', include('professeurs.urls')),
    path('administration/', include('administration.urls')),
    path('home/', include('Home.urls', namespace='Home')),

    
]