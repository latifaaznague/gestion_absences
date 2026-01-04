# urls.py
from django.urls import path
from . import views

app_name = "administration"

urlpatterns = [
    path("", views.admin_dashboard, name="admin_dashboard"),
    
    # Courses
    path("cours/", views.cours_list, name="cours_list"),
    path("cours/new/", views.cours_create, name="cours_create"),
    path("cours/<int:pk>/edit/", views.cours_edit, name="cours_edit"),
    path("cours/<int:course_id>/delete/", views.cours_delete, name="cours_delete"),
    
    # Auth & Profile
    path('logout/', views.admin_logout, name='logout'),
    path('profile/', views.admin_profile, name='admin_profile'),
    
    # Students
    path("etudiants/", views.student_list, name="student_list"),
    path("etudiants/new/", views.student_create, name="student_create"),
    path("etudiants/<int:student_id>/edit/", views.student_edit, name="student_edit"),
    path("etudiants/<int:student_id>/delete/", views.student_delete, name="student_delete"),
    
    # Absences
    path("etudiants/absences/", views.students_absences, name="students_absences"),
    
    # Planning
    path("planning/", views.planning_home, name="planning_home"),
    path("planning/day/", views.planning_day, name="planning_day"),
    path("planning/week/", views.planning_week, name="planning_week"),
    path("planning/generate/", views.planning_generate, name="planning_generate"),
    
    # Séances
    path('seance/add/', views.seance_add, name='seance_add'),
    path('seance/edit/<int:seance_id>/', views.seance_edit, name='seance_edit'),
    path('seance/delete/<int:seance_id>/', views.seance_delete, name='seance_delete'),
]