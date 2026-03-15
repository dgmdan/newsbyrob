from django.urls import path

from .views import ArticleListView

app_name = "newsfeed"

urlpatterns = [
    path("", ArticleListView.as_view(), name="article_list"),
]
