import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# apis
API_SMS = "https://api.befiana.cloud"
API_SMS_KEY = "d8d9591325d841cc8cf2b16f8cfef144"
API_ID_SMS = "8550940298539810000"

# send sms
API_SMS_SEND = f"{API_SMS}/api/smsko/v1/send/"
API_SMS_SOLDE = f"{API_SMS}/api/smsko/v1/balance/"




def send_sms_befiana(phone_number: str, message: str) -> dict:
    """
    Envoie un SMS via l'API Befiana SMSKO.
    
    :param phone_number: Numéro de téléphone destinataire
    :param message: Contenu du SMS
    :return: dict avec le résultat de l'API
    """


    # 🔐 Les en-têtes corrects
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": API_SMS_KEY,
    }

    payload = {
        "phone_number": phone_number,
        "message": message,
        "api_id": API_ID_SMS,
    }

    try:
        response = requests.post(API_SMS_SEND, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        result = response.json()
        logger.info(f"SMS envoyé avec succès à {phone_number}")
        return {
            "success": True,
            "status_code": response.status_code,
            "data": result,
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur API SMSKO : {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, "status_code", None),
        }
