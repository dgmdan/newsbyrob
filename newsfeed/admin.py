from django.contrib import admin

from .models import Article, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "site", "category", "pub_date"]
    search_fields = ["title", "description", "keyword"]
    list_filter = ["site", "category"]
    ordering = ["-pub_date", "-pull_date"]
