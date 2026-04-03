import logging
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from .models import Prestataire
from gasycar.utils import delete_file

logger = logging.getLogger(__name__)

def _cleanup_old_file(instance, field_name: str, model_class):
    """
    Supprime l'ancien fichier si un nouveau fichier est uploadé.
    """
    if not instance.pk:
        return

    try:
        previous = model_class.objects.get(pk=instance.pk)
    except model_class.DoesNotExist:
        return

    old_file = getattr(previous, field_name)
    new_file = getattr(instance, field_name)
    
    if old_file and old_file != new_file:
         if hasattr(old_file, 'url'):
             delete_file(old_file.url)
         elif hasattr(old_file, 'path'):
             delete_file(old_file.path)
         else:
             delete_file(str(old_file))

@receiver(pre_save, sender=Prestataire)
def prestataire_pre_save(sender, instance, **kwargs):
    # Liste des champs fichiers à surveiller
    file_fields = ['logo', 'nif_document', 'stat_document', 'rcs_document', 'cif_document']
    for field in file_fields:
        _cleanup_old_file(instance, field, Prestataire)

@receiver(pre_delete, sender=Prestataire)
def prestataire_pre_delete(sender, instance, **kwargs):
    # Suppression de tous les fichiers associés
    file_fields = ['logo', 'nif_document', 'stat_document', 'rcs_document', 'cif_document']
    for field in file_fields:
        file_obj = getattr(instance, field)
        if file_obj:
            if hasattr(file_obj, 'url'):
                 delete_file(file_obj.url)
            elif hasattr(file_obj, 'path'):
                 delete_file(file_obj.path)
            else:
                 delete_file(str(file_obj))
