from django.urls import path
from .views import etudiant_dashboard

urlpatterns = [
    path('dashboard/', etudiant_dashboard, name='etudiant_dashboard'),
]
