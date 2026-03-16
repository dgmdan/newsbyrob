import re

from django.db.models import Count, Q
from django.views.generic import ListView

from .models import Article, Tag


class ArticleListView(ListView):
    model = Article
    template_name = "newsfeed/article_list.html"
    context_object_name = "articles"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        tag_slug = self.request.GET.get("tag")
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)

        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            pattern = rf"\b{re.escape(search_query)}\b"
            queryset = queryset.filter(
                Q(title__iregex=pattern) | Q(description__iregex=pattern)
            )

        return queryset.prefetch_related("tags")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = (
            Tag.objects.annotate(article_count=Count("articles"))
            .filter(article_count__gt=0)
            .order_by("name")
        )
        context["active_tag"] = self.request.GET.get("tag")
        context["search_query"] = self.request.GET.get("q", "").strip()
        return context
