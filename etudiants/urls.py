# etudiants/urls.py
from django.urls import path
from . import views

app_name = 'etudiants'

urlpatterns = [
    # Redirige /etudiants/ selon la session
    path('', views.home_redirect, name='home'),
    path('logout/', views.logout, name='logout'),

    # Routes protégées
    path('dashboard/', views.dashboard_etudiant, name='dashboard_etudiant'),
    path('mes-presences/', views.mes_presences, name='mes_presences'),
    path('mes-notifications/', views.mes_notifications, name='mes_notifications'),
    path('ajouter-justification/<int:presence_id>/', views.ajouter_justification, name='ajouter_justification'),
    path('creer-notifications/', views.creer_notifications_pour_justifications, name='creer_notifications'),
   
]