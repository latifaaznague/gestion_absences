<<<<<<< HEAD
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
=======
from django.contrib import admin 
from django.urls import path, include 
from django.http import HttpResponse 
 
def home(request): 
    return HttpResponse("^<h1 style='text-align:center;margin-top:100px;color:#007bff;font-family:Arial;'>^<strong>AbsenceFlow^</strong>^<br>^<small>Hello ^</small>^</h1^>^<meta http-equiv='refresh'  />^") 
 
urlpatterns = [ 
    path('admin/', admin.site.urls), 
      path('etudiants/', include(('etudiants.urls', 'etudiants'), namespace='etudiants')),
    path('', home), 
    
] 
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
