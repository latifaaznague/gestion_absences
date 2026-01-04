# etudiants/context_processors.py
from .views import get_notifications_count

def notifications_context(request):
    """
    Context processor pour ajouter notifications_count à tous les templates
    """
    if 'etudiant_id' in request.session:
        try:
            count = get_notifications_count(request.session['etudiant_id'])
            return {'notifications_count': count}
        except:
            return {'notifications_count': 0}
    return {'notifications_count': 0}