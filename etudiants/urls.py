from django.urls import path
from . import views

app_name = 'etudiants'

urlpatterns = [
 path('login/', views.login_view, name='login_view'),
    path('dashboard/', views.dashboard_etudiant, name='dashboard_etudiant'),
    path('mes-presences/', views.mes_presences, name='mes_presences'),
<<<<<<< HEAD
    path('logout/', views.logout_view, name='logout_view'),
     path('ajouter-justification/<int:presence_id>/', views.ajouter_justification, name='ajouter_justification'),  # ← Ligne importante
      path('mes-notifications/', views.mes_notifications, name='mes_notifications'),
       path('creer-notifications/', views.creer_notifications_pour_justifications, name='creer_notifications'), 
    ]
=======
    path('mes-notifications/', views.mes_notifications, name='mes_notifications'),
    path('logout/', views.logout_view, name='logout_view'),
     path('ajouter-justification/<int:presence_id>/', views.ajouter_justification, name='ajouter_justification'),  # ← Ligne importante
]
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
