from django.core.management.base import BaseCommand
from django.utils import timezone
from blogs.models import BlogPost, BlogSection


class Command(BaseCommand):
    help = "Create blog post: Conseils pour un road trip réussi à Madagascar"

    def handle(self, *args, **kwargs):
        title = "Conseils pour un road trip réussi à Madagascar"
        subtitle = "Tout ce qu’il faut savoir pour voyager sur les routes malgaches en toute sérénité."
        excerpt = (
            "Préparer un road trip à Madagascar demande une bonne organisation : "
            "état des routes, saisons, sécurité, matériel indispensable et itinéraires. "
            "Voici un guide complet pour un voyage réussi."
        )

        if BlogPost.objects.filter(title=title).exists():
            self.stdout.write(self.style.WARNING("Cet article existe déjà."))
            return

        post = BlogPost.objects.create(
            title=title,
            subtitle=subtitle,
            excerpt=excerpt,
            is_published=True,
            published_at=timezone.now(),
            meta_title=title,
            meta_description=excerpt,
        )

        sections = [
            {
                "order": 1,
                "layout": "FULL",
                "title": "1. Choisissez la bonne saison",
                "body": (
                    "La saison sèche, de mai à octobre, est idéale pour un road trip. "
                    "Les routes sont plus praticables et les pluies sont rares, "
                    "ce qui réduit considérablement les risques de blocages."
                ),
                "image": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
                "list_items": ["Mai – Octobre : saison sèche", "Novembre – Avril : pluies fréquentes"],
            },
            {
                "order": 2,
                "layout": "IMAGE_RIGHT",
                "title": "2. Préparez-vous à des routes parfois difficiles",
                "body": (
                    "Beaucoup de routes à Madagascar sont en mauvais état. "
                    "Les routes nationales principales sont correctes, mais les pistes secondaires "
                    "peuvent être très dégradées, surtout après la saison des pluies."
                ),
                "image": "https://images.unsplash.com/photo-1505831694657-7209fed0cd36?auto=format&fit=crop&w=1200&q=80",
                "list_items": [
                    "Prévoir un 4x4 pour certaines régions",
                    "Éviter de conduire la nuit",
                    "Toujours vérifier l’état du véhicule avant de partir",
                ],
            },
            {
                "order": 3,
                "layout": "FULL",
                "title": "3. Louez un véhicule adapté au terrain",
                "body": (
                    "Pour un road trip confortable, privilégiez un SUV ou un 4x4. "
                    "De nombreux voyageurs choisissent également un chauffeur local pour éviter la fatigue."
                ),
                "cta_label": "Voir les véhicules conseillés",
                "cta_url": "https://madagasycar.com/voitures",
                "image": "https://images.unsplash.com/photo-1521133573892-e44906c9c270?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "order": 4,
                "layout": "IMAGE_LEFT",
                "title": "4. Préparez votre matériel indispensable",
                "body": (
                    "Un bon équipement vous évitera des galères sur la route. "
                    "Pensez à tout ce qui peut vous aider en cas de panne ou d’imprévu."
                ),
                "image": "https://images.unsplash.com/photo-1551739440-1a5dfcdbd4e1?auto=format&fit=crop&w=1200&q=80",
                "list_items": [
                    "GPS / Google Maps offline",
                    "Trousse de secours",
                    "Lampe frontale",
                    "Batterie externe",
                    "Eau et snacks",
                ],
            },
            {
                "order": 5,
                "layout": "FULL",
                "title": "5. Prévoyez des étapes réalistes",
                "body": (
                    "Les distances sont trompeuses à Madagascar. Une route de 200 km "
                    "peut prendre 6 à 8 heures selon l’état de la chaussée. "
                    "Planifiez des étapes courtes et profitez des paysages."
                ),
                "image": "https://images.unsplash.com/photo-1465447142348-e9952c393450?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "order": 6,
                "layout": "IMAGE_RIGHT",
                "title": "6. Respectez les règles de sécurité",
                "body": (
                    "La conduite de nuit est fortement déconseillée. "
                    "Soyez prudent dans les zones isolées et évitez de laisser "
                    "des objets visibles dans le véhicule."
                ),
                "image": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?auto=format&fit=crop&w=1200&q=80",
                "list_items": [
                    "Ne pas conduire la nuit",
                    "Toujours verrouiller les portes",
                    "Éviter les zones isolées",
                ],
            },
            {
                "order": 7,
                "layout": "FULL",
                "title": "7. Profitez des plus beaux itinéraires",
                "body": (
                    "Parmi les routes les plus populaires : la RN7 vers le sud, "
                    "la route côtière Tuléar–Ifaty, ou encore la route des lacs de l'Est. "
                    "Chacune offre des paysages uniques."
                ),
                "image": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1200&q=80",
            },
        ]

        for section in sections:
            BlogSection.objects.create(
                post=post,
                order=section["order"],
                layout=section["layout"],
                title=section.get("title", ""),
                body=section.get("body", ""),
                image=section.get("image"),
                list_items=section.get("list_items"),
                cta_label=section.get("cta_label"),
                cta_url=section.get("cta_url"),
            )

        self.stdout.write(self.style.SUCCESS("Blog créé : Road Trip Madagascar"))
