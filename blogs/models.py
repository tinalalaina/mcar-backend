import uuid
from django.db import models
from django.utils.text import slugify

class BlogPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, unique=True)

    cover_image = models.ImageField(upload_to="blog/covers/", blank=True, null=True)
    excerpt = models.TextField(blank=True)

    # SEO basique
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=255, blank=True)

    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            i = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class BlogSection(models.Model):
    class Layout(models.TextChoices):
        FULL = "FULL", "Full width"
        IMAGE_LEFT = "IMAGE_LEFT", "Image à gauche"
        IMAGE_RIGHT = "IMAGE_RIGHT", "Image à droite"
        QUOTE = "QUOTE", "Citation"

    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    order = models.PositiveIntegerField(default=0)

    layout = models.CharField(
        max_length=20,
        choices=Layout.choices,
        default=Layout.FULL,
    )

    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)

    image = models.ImageField(upload_to="blog/sections/", blank=True, null=True)

    # Liste d’items optionnelle (puces)
    list_items = models.JSONField(blank=True, null=True)  # ex: ["Point 1", "Point 2"]

    # CTA optionnel
    cta_label = models.CharField(max_length=100, blank=True)
    cta_url = models.URLField(blank=True)

    # Style optionnel (badge, tag, etc.)
    highlight_label = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.post.title} - {self.title or 'Section'}"
