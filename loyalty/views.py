from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reservations.models import Reservation
from reviews.models import Review

from .serializers import LoyaltyDashboardSerializer


LOYALTY_TIERS = [
    {
        "name": "Bronze",
        "min_points": 0,
        "max_points": 299,
        "threshold_label": "0 à 299 points",
        "perks": ["Accès au programme", "Historique des points"],
    },
    {
        "name": "Silver",
        "min_points": 300,
        "max_points": 799,
        "threshold_label": "300 à 799 points",
        "perks": ["Bonus ponctuels", "Offres fidélité"],
    },
    {
        "name": "Gold",
        "min_points": 800,
        "max_points": 1499,
        "threshold_label": "800 à 1 499 points",
        "perks": ["-10% sur certaines locations", "Avantages exclusifs", "Priorité promo"],
    },
    {
        "name": "Platinum",
        "min_points": 1500,
        "max_points": None,
        "threshold_label": "1 500+ points",
        "perks": ["Privilèges premium", "Bonus majorés", "Accès anticipé aux offres"],
    },
]


def calculate_reservation_points(reservation):
    amount = reservation.total_amount or 0
    return max(25, int(round(float(amount) / 10000)))


def has_completed_profile(user):
    required_values = [
        user.first_name,
        user.last_name,
        user.phone,
        user.address,
        user.date_of_birth,
        user.cin_number,
    ]
    required_files = [
        user.cin_photo_recto,
        user.cin_photo_verso,
        user.residence_certificate,
        user.permis_conduire_recto or user.permis_conduire,
    ]
    return all(bool(value) for value in required_values) and all(bool(value) for value in required_files)


class LoyaltyDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        completed_reservations = (
            Reservation.objects.filter(client=user, status=Reservation.Status.COMPLETED)
            .select_related("vehicle")
            .order_by("-end_datetime")
        )
        approved_reviews = (
            Review.objects.filter(
                author=user,
                moderation_status=Review.ModerationStatus.APPROVED,
                is_verified=True,
            )
            .select_related("reservation", "reservation__vehicle")
            .order_by("-created_at")
        )

        history = []
        reservation_points = 0
        for reservation in completed_reservations:
            points = calculate_reservation_points(reservation)
            reservation_points += points
            vehicle_name = getattr(reservation.vehicle, "modele", None) or getattr(reservation.vehicle, "nom", None) or "Location terminée"
            history.append(
                {
                    "id": f"reservation-{reservation.id}",
                    "title": f"Location terminée · {vehicle_name}",
                    "date": reservation.end_datetime,
                    "points": points,
                    "status": "earned",
                    "description": "Points crédités après une location finalisée avec succès.",
                    "source": "reservation",
                }
            )

        review_points = 0
        for review in approved_reviews:
            review_points += 25
            history.append(
                {
                    "id": f"review-{review.id}",
                    "title": "Avis vérifié publié",
                    "date": review.created_at,
                    "points": 25,
                    "status": "earned",
                    "description": "Bonus accordé pour un avis vérifié et approuvé.",
                    "source": "review",
                }
            )

        profile_bonus = 80 if has_completed_profile(user) else 0
        if profile_bonus:
            history.append(
                {
                    "id": f"profile-{user.id}",
                    "title": "Profil complété",
                    "date": user.updated_at or user.date_joined or timezone.now(),
                    "points": profile_bonus,
                    "status": "earned",
                    "description": "Bonus ponctuel accordé quand le profil et les documents requis sont complets.",
                    "source": "profile",
                }
            )

        history.sort(key=lambda item: item["date"], reverse=True)

        total_points = reservation_points + review_points + profile_bonus
        current_tier = LOYALTY_TIERS[0]
        next_tier = None
        for tier in LOYALTY_TIERS:
            max_points = tier["max_points"]
            if max_points is None or total_points <= max_points:
                current_tier = tier
                break
        for tier in LOYALTY_TIERS:
            if tier["min_points"] > total_points:
                next_tier = tier
                break

        min_points = current_tier["min_points"]
        max_points = current_tier["max_points"]
        if max_points is None:
            progress = 100.0
            points_to_next_tier = 0
            next_tier_label = ""
        else:
            span = max(max_points - min_points + 1, 1)
            progress = min(100.0, ((total_points - min_points + 1) / span) * 100)
            points_to_next_tier = max(0, (next_tier["min_points"] - total_points) if next_tier else 0)
            next_tier_label = next_tier["name"] if next_tier else ""

        tiers = []
        for tier in LOYALTY_TIERS:
            tiers.append({**tier, "active": tier["name"] == current_tier["name"]})

        discount_label = "Aucune remise active"
        if current_tier["name"] == "Gold":
            discount_label = "-10% sur certaines locations"
        elif current_tier["name"] == "Platinum":
            discount_label = "Remises premium et offres anticipées"
        elif current_tier["name"] == "Silver":
            discount_label = "Offres fidélité ponctuelles"

        payload = {
            "title": "Mes points fidélité",
            "subtitle": "Suivez votre progression, vos avantages et l'historique réel de vos gains fidélité.",
            "points": total_points,
            "next_tier_label": next_tier_label,
            "points_to_next_tier": points_to_next_tier,
            "progress": round(progress, 2),
            "member_since": timezone.localtime(user.date_joined).strftime("%B %Y"),
            "discount_label": discount_label,
            "current_tier": current_tier["name"],
            "profile_completed": bool(profile_bonus),
            "stats": [
                {
                    "label": "Niveau actuel",
                    "value": current_tier["name"],
                    "helper": "Votre niveau évolue automatiquement selon vos points validés.",
                },
                {
                    "label": "Points disponibles",
                    "value": str(total_points),
                    "helper": "Total calculé à partir des locations terminées, avis approuvés et bonus profil.",
                },
                {
                    "label": "Prochain palier",
                    "value": f"{points_to_next_tier} pts" if next_tier else "Palier max",
                    "helper": (
                        f"Encore {points_to_next_tier} points pour atteindre {next_tier_label}."
                        if next_tier
                        else "Vous avez atteint le palier le plus élevé du programme."
                    ),
                },
            ],
            "history": history,
            "tiers": tiers,
            "earning_rules": [
                {
                    "title": "Réserver et terminer une location",
                    "description": "Les points sont calculés automatiquement quand une réservation passe au statut terminée.",
                    "enabled": True,
                },
                {
                    "title": "Laisser un avis vérifié",
                    "description": "Un bonus de 25 points est accordé pour chaque avis vérifié et approuvé.",
                    "enabled": True,
                },
                {
                    "title": "Compléter votre profil",
                    "description": "Un bonus ponctuel de 80 points est accordé quand le profil et les documents sont complets.",
                    "enabled": True,
                },
                {
                    "title": "Parrainer un ami",
                    "description": "Hors périmètre pour le moment : cette mécanique est volontairement ignorée côté backend.",
                    "enabled": False,
                },
            ],
        }

        serializer = LoyaltyDashboardSerializer(payload)
        return Response(serializer.data)
