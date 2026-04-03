from django import forms
from .models import ReservationPayment

class ReservationPaymentForm(forms.ModelForm):
    class Meta:
        model = ReservationPayment
        fields = ("reservation", "mode", "reason", "proof_image")
        widgets = {
            "reservation": forms.HiddenInput(),
            "mode": forms.HiddenInput(),
            "reason": forms.HiddenInput(),
        }

    def clean_proof_image(self):
        img = self.cleaned_data.get("proof_image")
        if not img:
            raise forms.ValidationError("La preuve est requise.")
        if img.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La preuve doit être inférieure à 5MB.")
        return img
