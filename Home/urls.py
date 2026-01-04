from django.urls import path
from . import views

app_name = 'Home'  # <-- C'est ici qu'on définit le namespace

urlpatterns = [
    path('', views.index, name='index'),
   
    # ... autres URLs
]