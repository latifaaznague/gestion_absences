# Home/apps.py
from django.apps import AppConfig

class HomeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Home'
    
    def ready(self):
        # Importez les signaux
        import Home.signals