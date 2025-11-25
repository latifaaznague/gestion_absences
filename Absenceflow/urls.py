from django.contrib import admin 
from django.urls import path, include 
from django.http import HttpResponse 
 
def home(request): 
    return HttpResponse("^<h1 style='text-align:center;margin-top:100px;color:#007bff;font-family:Arial;'>^<strong>AbsenceFlow^</strong>^<br>^<small>Hello ^</small>^</h1^>^<meta http-equiv='refresh'  />^") 
 
urlpatterns = [ 
    path('admin/', admin.site.urls), 
    path('', home), 
] 
