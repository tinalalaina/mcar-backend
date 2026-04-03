from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from .models import User
from gasycar.utils import delete_file


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
        if hasattr(old_file, "path"):
            delete_file(old_file.path)
        elif hasattr(old_file, "url"):
            delete_file(old_file.url)


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    # Image de profil
    _cleanup_old_file(instance, "image", User)

    # CIN recto / verso
    _cleanup_old_file(instance, "cin_photo_recto", User)
    _cleanup_old_file(instance, "cin_photo_verso", User)
    _cleanup_old_file(instance, "permis_conduire", User)
    _cleanup_old_file(instance, "permis_conduire_recto", User)
    _cleanup_old_file(instance, "permis_conduire_verso", User)


@receiver(pre_delete, sender=User)
def delete_user_files(sender, instance, **kwargs):
    """
    Lorsqu'un user est supprimé → supprimer ses fichiers physiques
    """
    if instance.image:
        delete_file(instance.image.path)

    if instance.cin_photo_recto:
        delete_file(instance.cin_photo_recto.path)

    if instance.cin_photo_verso:
        delete_file(instance.cin_photo_verso.path)

    if instance.permis_conduire:
        delete_file(instance.permis_conduire.path)

    if instance.permis_conduire_recto:
        delete_file(instance.permis_conduire_recto.path)

    if instance.permis_conduire_verso:
        delete_file(instance.permis_conduire_verso.path)
