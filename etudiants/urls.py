from django.urls import path
from . import views

app_name = 'etudiants'

urlpatterns = [
 path('login/', views.login_view, name='login_view'),
    path('dashboard/', views.dashboard_etudiant, name='dashboard_etudiant'),
    path('mes-presences/', views.mes_presences, name='mes_presences'),
    path('mes-notifications/', views.mes_notifications, name='mes_notifications'),
    path('logout/', views.logout_view, name='logout_view'),
     path('ajouter-justification/<int:presence_id>/', views.ajouter_justification, name='ajouter_justification'),  # ← Ligne importante
]
