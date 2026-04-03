from rest_framework import serializers
from gasycar.utils import delete_file
from .models import BlogPost, BlogSection


class BlogSectionSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    cta_url = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = BlogSection
        fields = [
            "id",
            "order",
            "layout",
            "title",
            "body",
            "image",
            "list_items",
            "cta_label",
            "cta_url",
            "highlight_label",
        ]

    def validate_cta_url(self, value):
        if not value:
            return value
        if value.startswith("/"):
            return value
        if value.startswith("http://") or value.startswith("https://"):
            return value
        raise serializers.ValidationError("CTA URL doit être une URL absolue (http/https) ou un chemin relatif commençant par /.")


class BlogPostSerializer(serializers.ModelSerializer):
    sections = BlogSectionSerializer(many=True, required=False)
    cover_image = serializers.ImageField(required=False)

    class Meta:
        model = BlogPost
        fields = [
            "id",
            "title",
            "subtitle",
            "slug",
            "cover_image",
            "excerpt",
            "meta_title",
            "meta_description",
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
            "sections",
        ]
        read_only_fields = ("created_at", "updated_at", "published_at")

    def create(self, validated_data):
        sections_data = validated_data.pop("sections", [])
        post = BlogPost.objects.create(**validated_data)

        for section in sections_data:
            BlogSection.objects.create(post=post, **section)

        return post

    def update(self, instance, validated_data):
        sections_data = validated_data.pop("sections", None)

        if "cover_image" in validated_data and instance.cover_image:
            delete_file(instance.cover_image.url)

        # Update blog info
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update sections
        if sections_data is not None:
            # Nettoyer les anciennes images avant suppression
            for section in instance.sections.all():
                if section.image:
                    delete_file(section.image.url)
            instance.sections.all().delete()
            for section in sections_data:
                BlogSection.objects.create(post=instance, **section)

        return instance
