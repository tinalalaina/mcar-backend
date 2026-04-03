import logging
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from .models import ModePayment
from gasycar.utils import delete_file

logger = logging.getLogger(__name__)

def _cleanup_old_file(instance, field_name: str, model_class):
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

@receiver(pre_save, sender=ModePayment)
def modepayment_pre_save(sender, instance, **kwargs):
    _cleanup_old_file(instance, "image", ModePayment)

@receiver(pre_delete, sender=ModePayment)
def modepayment_pre_delete(sender, instance, **kwargs):
    if instance.image:
        if hasattr(instance.image, 'url'):
             delete_file(instance.image.url)
        elif hasattr(instance.image, 'path'):
             delete_file(instance.image.path)
        else:
             delete_file(str(instance.image))
