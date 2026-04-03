from django.core.mail import EmailMessage
from django.utils import timezone
from datetime import timedelta
import random
from users.models import User, OTPCode
from django.template.loader import render_to_string


import logging
import os
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import default_storage


# ==================Auto send email======================

class Util:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data["email_subject"],
            body=data["email_body"],
            to=[data["to_email"]],
        )
        email.content_subtype = "html"
        email.send()
        

        
def send_email_notification(email_content, email, titre, is_html=True):
    content = {
        "email_body": email_content,
        "to_email": email,
        "email_subject": titre,
        "is_html": is_html  # Spécifier que c'est du HTML
    }
    Util.send_email(content)
    
    

def generate_otp_code():
    return f"{random.randint(100000, 999999)}"

def create_and_send_email_otp(user: User) -> OTPCode:
    """
    Crée et envoie un OTP par email pour la vérification d'email
    Sans import circulaire
    """
    from users.services import OTPService  # Import local pour éviter le circulaire
    
    # Utilisez le service OTP existant
    otp = OTPService.create_otp(user, 'email_verification')
    subject = "Vérification de votre adresse email - GasyCar"
    
    html_message = render_to_string(
                "otp.html",
                { "OTP_CODE": otp.code},
            )
    # send avec is_html=True
    send_email_notification(html_message, user.email, subject, is_html=True)
    return otp

# Fonction alternative autonome (sans dépendance à OTPService)
def create_and_send_email_otp_standalone(user: User) -> OTPCode:
    """
    Version autonome qui ne dépend pas de OTPService
    """
    # Efface les anciens OTP non utilisés pour email_verification
    OTPCode.objects.filter(
        user=user, 
        purpose='email_verification', 
        is_used=False
    ).delete()

    code = generate_otp_code()
    now = timezone.now()
    otp = OTPCode.objects.create(
        user=user,
        code=code,
        purpose='email_verification',
        expires_at=now + timedelta(minutes=10),
    )
    
    subject = "Vérification de votre adresse email - GasyCar"
    # Message texte simple
    html_message = render_to_string(
                "otp.html",
                { "OTP_CODE": otp.code},
            )
    # send avec is_html=True
    send_email_notification(html_message, user.email, subject, is_html=True)
    return otp


logger = logging.getLogger(__name__)


def _normalize_media_path(path_or_url: str) -> str | None:
    """
    Convertit un chemin relatif ou une URL complète vers un chemin relatif
    dans MEDIA_ROOT pour que le storage puisse le supprimer.
    """
    if not path_or_url:
        return None

    path_or_url = str(path_or_url)
    parsed = urlparse(path_or_url)

    # URL complète → on garde uniquement le path
    if parsed.scheme and parsed.netloc:
        candidate = parsed.path
    else:
        candidate = path_or_url

    # Retire MEDIA_URL si présent et nettoie les slashs initiaux
    if settings.MEDIA_URL and candidate.startswith(settings.MEDIA_URL):
        candidate = candidate.replace(settings.MEDIA_URL, "", 1)
    candidate = candidate.lstrip("/")

    if not candidate:
        return None
    return candidate


def delete_file(path_or_url: str):
    """
    Supprime silencieusement un fichier stocké dans MEDIA_ROOT.

    - Accepte une URL absolue, une URL relative ou un chemin relatif.
    - Ignore toute erreur si le fichier n'existe plus.
    """
    relative_path = _normalize_media_path(path_or_url)
    if not relative_path:
        return

    try:
        if default_storage.exists(relative_path):
            default_storage.delete(relative_path)
            return

        # Fallback local : peut arriver si storage custom mais MEDIA_ROOT accessible
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
    except Exception as exc:
        logger.warning("Impossible de supprimer le fichier %s : %s", relative_path, exc)