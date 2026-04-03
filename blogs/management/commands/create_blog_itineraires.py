from django.core.management.base import BaseCommand
from django.utils import timezone
from blogs.models import BlogPost, BlogSection


class Command(BaseCommand):
    help = "Create blog post: Itinéraires incontournables pour découvrir Madagascar"

    def handle(self, *args, **kwargs):
        title = "Itinéraires incontournables pour découvrir Madagascar"
        subtitle = (
            "RN7, côte ouest, îles du nord… Voici les meilleurs itinéraires pour découvrir Madagascar."
        )
        excerpt = (
            "Madagascar est une île immense avec des paysages variés : déserts, jungles, plages, montagnes, baobabs. "
            "Voici les itinéraires recommandés pour un voyage complet."
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
                "title": "1. La RN7 : l'itinéraire classique du sud",
                "body": (
                    "La RN7 est l’itinéraire le plus populaire : Antananarivo → Antsirabe → Ranomafana → Isalo → Tuléar. "
                    "Un mélange parfait de culture, nature et paysages spectaculaires."
                ),
                "image": "https://images.unsplash.com/photo-1549880338-65ddcdfd017b?auto=format&fit=crop&w=1200&q=80",
                "list_items": [
                    "Antsirabe : ville thermale",
                    "Ranomafana : forêt tropicale",
                    "Isalo : canyons et piscines naturelles",
                    "Ifaty : plages et lagons",
                ],
            },
            {
                "order": 2,
                "layout": "IMAGE_LEFT",
                "title": "2. La côte ouest : baobabs et Tsingy",
                "body": (
                    "Pour ceux qui aiment l’aventure : Morondava, l’Allée des Baobabs et les Tsingy de Bemaraha. "
                    "Un voyage spectaculaire et sauvage."
                ),
                "image": "https://images.unsplash.com/photo-1605276374104-e3c6956c17af?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "order": 3,
                "layout": "IMAGE_RIGHT",
                "title": "3. Le nord : Nosy Be et Diego Suarez",
                "body": (
                    "Le nord de Madagascar offre certaines des plus belles plages du pays. "
                    "Diego Suarez et Nosy Be sont parfaits pour un voyage détente."
                ),
                "image": "https://images.unsplash.com/photo-1584467735871-ea86fb63b2f3?auto=format&fit=crop&w=1200&q=80",
                "list_items": ["Mer d’Émeraude", "Montagne des Français", "Plages paradisiaques"],
            },
            {
                "order": 4,
                "layout": "FULL",
                "title": "4. L’Est : forêts tropicales et île Sainte-Marie",
                "body": (
                    "C'est la région des forêts humides, des lémuriens et de la côte sauvage. "
                    "Sainte-Marie est un paradis calme, idéal pour les familles et couples."
                ),
                "image": "https://images.unsplash.com/photo-1604584976203-3cfa3cc585e9?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "order": 5,
                "layout": "FULL",
                "title": "5. Itinéraires conseillés selon la durée",
                "body": (
                    "• 7 jours : RN7 express\n"
                    "• 10 jours : RN7 + Ifaty\n"
                    "• 14 jours : RN7 + Tsingy ou Sainte-Marie\n"
                    "• 21 jours : tour combiné nord/sud"
                ),
                "image": "https://images.unsplash.com/photo-1534080564583-6be75777b70a?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "order": 6,
                "layout": "IMAGE_RIGHT",
                "title": "Besoin d’un itinéraire sur mesure ?",
                "body": (
                    "Madagasycar propose des véhicules adaptés et des chauffeurs professionnels "
                    "pour organiser votre voyage."
                ),
                "cta_label": "Voir nos voitures",
                "cta_url": "https://madagasycar.com/voitures",
                "image": "https://images.unsplash.com/photo-1498062477267-7ea23c84cd74?auto=format&fit=crop&w=1200&q=80",
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

        self.stdout.write(self.style.SUCCESS("Blog créé : Itinéraires Madagascar"))
