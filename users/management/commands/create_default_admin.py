from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import OperationalError, ProgrammingError

from users.models import User  # adapte le chemin si besoin


class Command(BaseCommand):
    help = "Crée un super admin par défaut s'il n'existe pas déjà."

    def handle(self, *args, **options):
        admin_email = getattr(settings, "DEFAULT_ADMIN_EMAIL", None)
        admin_password = getattr(settings, "DEFAULT_ADMIN_PASSWORD", None)
        first_name = getattr(settings, "DEFAULT_ADMIN_FIRST_NAME", "Super")
        last_name = getattr(settings, "DEFAULT_ADMIN_LAST_NAME", "Admin")

        if not admin_email or not admin_password:
            self.stdout.write(
                self.style.ERROR(
                    "Les variables DEFAULT_ADMIN_EMAIL et DEFAULT_ADMIN_PASSWORD ne sont pas définies dans settings."
                )
            )
            return

        try:
            # Vérifier si un superuser avec cet email existe déjà
            if User.objects.filter(email=admin_email, is_superuser=True).exists():
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Un super admin avec l'email {admin_email} existe déjà. Rien à faire."
                    )
                )
                return

            # Créer le superuser
            user = User.objects.create_superuser(
                email=admin_email,
                password=admin_password,
                first_name=first_name,
                last_name=last_name,
                role="ADMIN",          # très important pour ton modèle
                email_verified=True,   # tu as ce champ dans ton modèle
                phone_verified=True,   # optionnel si tu veux
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Super admin créé avec succès : {user.email}"
                )
            )

        except (OperationalError, ProgrammingError) as e:
            # Par exemple : table users pas encore migrée
            self.stdout.write(
                self.style.ERROR(
                    f"Erreur lors de la création du super admin (probablement avant les migrations) : {e}"
                )
            )
