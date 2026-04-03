from django.contrib import admin
from .models import BlogPost, BlogSection

class BlogSectionInline(admin.TabularInline):
    model = BlogSection
    extra = 1
    fields = (
        "order",
        "layout",
        "title",
        "highlight_label",
        "image",
        "body",
        "list_items",
        "cta_label",
        "cta_url",
    )

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at", "created_at")
    list_filter = ("is_published", "published_at", "created_at")
    search_fields = ("title", "subtitle", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [BlogSectionInline]

@admin.register(BlogSection)
class BlogSectionAdmin(admin.ModelAdmin):
    list_display = ("post", "order", "layout", "title")
    list_filter = ("layout", "post")
    search_fields = ("title", "body")
