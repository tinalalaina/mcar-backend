from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import OperationalError, ProgrammingError
import os

from users.models import User  # adapte le chemin si besoin


class Command(BaseCommand):
    help = "Crée un super SUPPORT par défaut s'il n'existe pas déjà."

    def handle(self, *args, **options):
        email =os.environ.get( "DEFAULT_SUPPORT_EMAIL", None)
        password =os.environ.get( "DEFAULT_SUPPORT_PASSWORD", None)
        first_name =os.environ.get( "DEFAULT_SUPPORT_FIRST_NAME", "Super")
        last_name =os.environ.get( "DEFAULT_SUPPORT_LAST_NAME", "Admin")

        if not email or not password:
            self.stdout.write(
                self.style.ERROR(
                    "Les variables DEFAULT_ADMIN_EMAIL et DEFAULT_password ne sont pas définies dans settings."
                )
            )
            return

        try:
            # Vérifier si un superuser avec cet email existe déjà
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Un super admin avec l'email {email} existe déjà. Rien à faire."
                    )
                )
                return

            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role="SUPPORT",          # très important pour ton modèle
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
