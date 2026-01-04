from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),   
     
    path('accounts/', include('accounts.urls', namespace='accounts')),  # ✅
    path("etudiants/", include("etudiants.urls")),
    
    path("administration/", include("administration.urls")),
    path('', include('Home.urls', namespace='Home')),  
              
     #professeurs         
   path('professeurs/', include('professeurs.urls')),  # Inclure les URLs des profes
]
