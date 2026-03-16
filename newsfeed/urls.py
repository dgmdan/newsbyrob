from django.urls import path

from .feeds import LatestArticlesFeed
from .views import ArticleListView

app_name = "newsfeed"

urlpatterns = [
    path("feed/", LatestArticlesFeed(), name="feed"),
    path("", ArticleListView.as_view(), name="article_list"),
]
