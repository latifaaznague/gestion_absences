# setup_django.py
import os
import django
import sys

# Définir le module de settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_absences.settings')

# Configurer Django
django.setup()

print("✅ Django configuré avec succès!")