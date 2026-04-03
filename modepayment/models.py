from django.db import models
import uuid

# Create your models here.
class ModePayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operateur = models.CharField(max_length=255,blank=True,null=True)
    name = models.CharField(max_length=255)
    numero = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to="modepayment/photos/",blank=True,null=True)
    is_active = models.BooleanField(default=True)  # ✔️ utile pour filtrer

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Mode de paiement-{self.name}"