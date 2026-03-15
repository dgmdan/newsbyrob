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
        return queryset.prefetch_related("tags")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = Tag.objects.order_by("name")
        context["active_tag"] = self.request.GET.get("tag")
        return context
