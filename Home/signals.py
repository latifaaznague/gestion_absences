# Home/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Presence

@receiver(pre_save, sender=Presence)
def capturer_ancien_statut_justification(sender, instance, **kwargs):
    """
    Capture l'ancien statut de justification avant la sauvegarde
    """
    try:
        if instance.pk:
            ancien = Presence.objects.get(pk=instance.pk)
            instance._old_statut_justification = ancien.statut_justification
        else:
            instance._old_statut_justification = None
    except Presence.DoesNotExist:
        instance._old_statut_justification = None