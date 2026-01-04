from django.urls import path
from . import views

app_name = 'professeurs'

urlpatterns = [
    # Login/Logout
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    
    # Dashboard
    path('dashboard/', views.dashboard_professeur, name='dashboard_professeur'),
     # Profil
    path('profil/', views.profil_professeur, name='profil_professeur'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    
    # Pages en construction
    path('cours/', views.mes_cours, name='mes_cours'),
    path('cours/<int:cours_id>/', views.detail_cours, name='detail_cours'),
    path('prendre-presences/<int:seance_id>/', views.prendre_presences,name='prendre_presences'),
    path('seances/', views.mes_seances, name='mes_seances'),
     # Justifications
    path('justifications/', views.justifications_attente, name='justifications_attente'),
    path('justifications/<int:presence_id>/', views.voir_justification, name='voir_justification'),
    path('justifications/<int:presence_id>/traiter/', views.traiter_justification, name='traiter_justification'),
    path('justifications/<int:presence_id>/telecharger/', views.telecharger_fichier_justificatif, name='telecharger_fichier_justificatif'),
    path('justifications/<int:presence_id>/afficher/', views.afficher_fichier, name='afficher_fichier'),  # NOUVELLE URL
    path('afficher-fichier/<int:presence_id>/', views.afficher_fichier_modal, name='afficher_fichier_modal'),
    
    ]