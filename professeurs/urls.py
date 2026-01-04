# professeurs/urls.py - VÉRIFIEZ QUE TOUTES CES URLS EXISTENT
from django.urls import path
from . import views

app_name = 'professeurs'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_professeur, name='dashboard'),
    path('dashboard/', views.dashboard_professeur, name='dashboard_professeur'),
    
    # Cours
    path('cours/', views.mes_cours, name='mes_cours'),
    path('cours/<int:cours_id>/', views.detail_cours, name='detail_cours'),
    
    # Séances
    path('seances/', views.mes_seances, name='mes_seances'),
    path('prendre-presences/<int:seance_id>/', views.prendre_presences, name='prendre_presences'),
    
    # Justifications
    path('justifications/', views.justifications_attente, name='justifications_attente'),
    path('justifications/<int:presence_id>/', views.voir_justification, name='voir_justification'),
    path('justifications/<int:presence_id>/traiter/', views.traiter_justification, name='traiter_justification'),
    path('justifications/<int:presence_id>/telecharger/', views.telecharger_fichier_justificatif, name='telecharger_fichier_justificatif'),
    path('justifications/<int:presence_id>/afficher-modal/', views.afficher_fichier_modal, name='afficher_fichier_modal'),
    path('justifications/<int:presence_id>/afficher/', views.afficher_fichier, name='afficher_fichier'),
    
    # Profil
    path('profil/', views.profil_professeur, name='profil_professeur'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    # Logout (namespaced for templates still referencing 'professeurs:logout_view')
    path('logout/', views.logout_view, name='logout_view'),

    # Diagnostic / Test
    path('test-pdf/', views.test_pdf, name='test_pdf'),
    path('presence-file-info/<int:presence_id>/', views.presence_file_info, name='presence_file_info'),
    path('presence-stats/', views.presence_stats, name='presence_stats'),
    

]