from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from bs4 import BeautifulSoup
from newsfeed.management.commands.collect_news import normalize_external_id
from newsfeed.models import Article, Tag
from newsfeed.url_resolver import ResolvedURL, resolve_final_url
from scripts.aila import get_articles
from scripts.feed_config import NewArticle


class NewsfeedViewsTestCase(TestCase):
    def setUp(self):
        self.tag = Tag.objects.create(name="Updates")
        self.other_tag = Tag.objects.create(name="Alerts")
        self.article = Article.objects.create(
            external_id="test-1",
            title="Test Article",
            link="https://example.com/1",
            description="<p>Summary</p>",
            pub_date=timezone.now(),
            pull_date=timezone.now(),
        )
        self.article.tags.add(self.tag)
        self.other_article = Article.objects.create(
            external_id="test-2",
            title="Second Article",
            link="https://example.com/2",
            description="<p>Other Summary</p>",
            pub_date=timezone.now(),
            pull_date=timezone.now(),
        )
        self.other_article.tags.add(self.other_tag)

    def test_homepage_shows_articles(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "newsfeed/article_list.html")
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.other_article.title)

    def test_tag_filter_limits_results(self):
        response = self.client.get("/", {"tag": self.tag.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.assertNotContains(response, self.other_article.title)


class CollectNewsCommandTestCase(TestCase):
    @patch("newsfeed.management.commands.collect_news.send_email_update", return_value=False)
    @patch("newsfeed.management.commands.collect_news.resolve_final_url", return_value=ResolvedURL(url="https://example.com/final"))
    def test_collect_news_creates_articles(self, mock_resolve, mock_send_email):
        now = timezone.now()

        dummy_article = NewArticle(
            id="dummy-1",
            title="Dummy title",
            link="https://example.com/dummy",
            description="<p>Dummy description</p>",
            pub_date=now,
            pull_date=now,
            category="Dummy",
            source="Dummy Source",
        )

        class DummyModule:
            def ingest_xml(self, cat, source, NewArticleClass):
                return [dummy_article]

        with patch(
            "newsfeed.management.commands.collect_news.SITES",
            {"Dummy Site": ("https://example.com", DummyModule())},
        ), patch(
            "newsfeed.management.commands.collect_news.CATEGORIES",
            {"Dummy Site": ["Dummy"]},
        ):
            call_command("collect_news")

        self.assertTrue(Article.objects.filter(external_id="dummy-1").exists())
        created_article = Article.objects.get(external_id="dummy-1")
        self.assertEqual(created_article.title, "Dummy title")
        self.assertEqual(created_article.source, "Dummy Source")
        self.assertEqual(created_article.category, "Dummy")
        mock_send_email.assert_called_once()

    @patch("newsfeed.management.commands.collect_news.send_email_update", return_value=False)
    @patch("newsfeed.management.commands.collect_news.resolve_final_url", return_value=ResolvedURL(url="https://example.com/final"))
    def test_collect_news_normalizes_long_external_id(self, mock_resolve, mock_send_email):
        now = timezone.now()
        long_id = "x" * 1024

        dummy_article = NewArticle(
            id=long_id,
            title="Dummy title",
            link="https://example.com/dummy",
            description="<p>Dummy description</p>",
            pub_date=now,
            pull_date=now,
            category="Dummy",
            source="Dummy Source",
        )

        class DummyModule:
            def ingest_xml(self, cat, source, NewArticleClass):
                return [dummy_article]

        with patch(
            "newsfeed.management.commands.collect_news.SITES",
            {"Dummy Site": ("https://example.com", DummyModule())},
        ), patch(
            "newsfeed.management.commands.collect_news.CATEGORIES",
            {"Dummy Site": ["Dummy"]},
        ):
            call_command("collect_news")

        expected_external_id = normalize_external_id(long_id)
        self.assertTrue(Article.objects.filter(external_id=expected_external_id).exists())
        created_article = Article.objects.get(external_id=expected_external_id)
        max_length = Article._meta.get_field("external_id").max_length
        self.assertLessEqual(len(created_article.external_id), max_length)
        self.assertEqual(created_article.external_id, expected_external_id)
        mock_send_email.assert_called_once()

    @patch("newsfeed.management.commands.collect_news.send_email_update", return_value=False)
    @patch("newsfeed.management.commands.collect_news.resolve_final_url", return_value=ResolvedURL(url="https://www.politico.com/news/2026/07/01/after-supreme-court-loss-on-birthright-citizenship-white-house-eyes-crackdown-on-pregnant-foreigners-00984187"))
    def test_collect_news_saves_final_destination_url(self, mock_resolve, mock_send_email):
        now = timezone.now()

        dummy_article = NewArticle(
            id="dummy-redirect-1",
            title="Dummy title",
            link="https://linkprotect.cudasvc.com/url?a=https%3a%2f%2fus.list-manage.com%2f13ilg5J_cOD",
            description="<p>Dummy description</p>",
            pub_date=now,
            pull_date=now,
            category="Dummy",
            source="Dummy Source",
        )

        class DummyModule:
            def ingest_xml(self, cat, source, NewArticleClass):
                return [dummy_article]

        with patch(
            "newsfeed.management.commands.collect_news.SITES",
            {"Dummy Site": ("https://example.com", DummyModule())},
        ), patch(
            "newsfeed.management.commands.collect_news.CATEGORIES",
            {"Dummy Site": ["Dummy"]},
        ):
            call_command("collect_news")

        created_article = Article.objects.get(external_id="dummy-redirect-1")
        self.assertEqual(
            created_article.link,
            "https://www.politico.com/news/2026/07/01/after-supreme-court-loss-on-birthright-citizenship-white-house-eyes-crackdown-on-pregnant-foreigners-00984187",
        )
        mock_send_email.assert_called_once()

    @patch("newsfeed.management.commands.collect_news.send_email_update", return_value=False)
    @patch("newsfeed.management.commands.collect_news.resolve_final_url")
    def test_collect_news_keeps_gov_links_without_resolving(self, mock_resolve, mock_send_email):
        now = timezone.now()

        dummy_article = NewArticle(
            id="dummy-gov-1",
            title="Gov title",
            link="https://www.congress.gov/bill/119th-congress/house-bill/1",
            description="<p>Dummy description</p>",
            pub_date=now,
            pull_date=now,
            category="Dummy",
            source="Dummy Source",
        )

        class DummyModule:
            def ingest_xml(self, cat, source, NewArticleClass):
                return [dummy_article]

        with patch(
            "newsfeed.management.commands.collect_news.SITES",
            {"Dummy Site": ("https://example.com", DummyModule())},
        ), patch(
            "newsfeed.management.commands.collect_news.CATEGORIES",
            {"Dummy Site": ["Dummy"]},
        ):
            call_command("collect_news")

        created_article = Article.objects.get(external_id="dummy-gov-1")
        self.assertEqual(created_article.link, "https://www.congress.gov/bill/119th-congress/house-bill/1")
        mock_resolve.assert_not_called()
        mock_send_email.assert_called_once()


class UrlResolverTestCase(TestCase):
    @patch("newsfeed.url_resolver.requests.get")
    def test_resolve_final_url_returns_terminal_url_even_on_forbidden(self, mock_get):
        final = SimpleNamespace(
            status_code=403,
            url="https://www.politico.com/news/2026/07/01/after-supreme-court-loss-on-birthright-citizenship-white-house-eyes-crackdown-on-pregnant-foreigners-00984187",
            is_redirect=False,
            is_permanent_redirect=False,
            headers={},
        )
        mock_get.return_value.__enter__.return_value = final

        resolved = resolve_final_url("https://linkprotect.cudasvc.com/url?a=tracker")
        self.assertEqual(resolved.url, final.url)
        self.assertFalse(resolved.rate_limited)

    @patch("newsfeed.url_resolver.requests.get")
    def test_resolve_final_url_stops_on_redirect_loop_after_ten_hops(self, mock_get):
        responses = []
        for _ in range(11):
            response = SimpleNamespace(
                status_code=302,
                url="https://linkprotect.cudasvc.com/url?a=tracker",
                is_redirect=True,
                is_permanent_redirect=False,
                headers={"Location": "https://linkprotect.cudasvc.com/url?a=tracker"},
            )
            response.__enter__ = lambda self=response: self
            response.__exit__ = lambda *args: None
            responses.append(response)

        mock_get.side_effect = responses

        resolved = resolve_final_url("https://linkprotect.cudasvc.com/url?a=tracker")
        self.assertEqual(resolved.url, "https://linkprotect.cudasvc.com/url?a=tracker")
        self.assertFalse(resolved.rate_limited)


class BackfillLinksCommandTestCase(TestCase):
    @patch("newsfeed.management.commands.backfill_final_links.time.sleep")
    @patch("newsfeed.management.commands.backfill_final_links.resolve_final_url")
    def test_backfill_rewrites_links_with_delay(self, mock_resolve, mock_sleep):
        article1 = Article.objects.create(
            external_id="a1",
            title="A1",
            link="https://linkprotect.cudasvc.com/url?a=one",
        )
        article2 = Article.objects.create(
            external_id="a2",
            title="A2",
            link="https://linkprotect.cudasvc.com/url?a=two",
        )
        mock_resolve.side_effect = [
            ResolvedURL(url="https://www.politico.com/a1"),
            ResolvedURL(url="https://www.politico.com/a2"),
        ]

        call_command("backfill_final_links", delay=0.25)

        article1.refresh_from_db()
        article2.refresh_from_db()
        self.assertEqual(article1.link, "https://www.politico.com/a1")
        self.assertEqual(article2.link, "https://www.politico.com/a2")
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("newsfeed.management.commands.backfill_final_links.time.sleep")
    @patch("newsfeed.management.commands.backfill_final_links.resolve_final_url")
    def test_backfill_skips_gov_links_without_resolving(self, mock_resolve, mock_sleep):
        article = Article.objects.create(
            external_id="a4",
            title="A4",
            link="https://www.congress.gov/bill/119th-congress/house-bill/1",
        )

        call_command("backfill_final_links", delay=0.25)

        article.refresh_from_db()
        self.assertEqual(
            article.link,
            "https://www.congress.gov/bill/119th-congress/house-bill/1",
        )
        mock_resolve.assert_not_called()
        self.assertEqual(mock_sleep.call_count, 1)

    @patch("newsfeed.management.commands.backfill_final_links.time.sleep")
    @patch("newsfeed.management.commands.backfill_final_links.resolve_final_url")
    def test_backfill_skips_rate_limited_articles(self, mock_resolve, mock_sleep):
        article = Article.objects.create(
            external_id="a3",
            title="A3",
            link="https://linkprotect.cudasvc.com/url?a=rate-limited",
        )
        mock_resolve.return_value = ResolvedURL(url=article.link, rate_limited=True)

        call_command("backfill_final_links", delay=0.25)

        article.refresh_from_db()
        self.assertEqual(article.link, "https://linkprotect.cudasvc.com/url?a=rate-limited")
        self.assertEqual(mock_sleep.call_count, 1)


class AilaScraperTestCase(TestCase):
    def test_description_prefers_article_text_over_section_label(self):
        html = """
        <div class="typography text rte">
            <h2><em>National</em></h2>
            <p>
                <em>NPR</em>
                <a href="https://www.npr.org/article">ICE's detention expansion meets resistance</a>
                <br/>
                By Jasmine Garsd
            </p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = get_articles(
            soup.find("div", class_="typography text rte"),
            "AILA Daily News Update",
            "https://www.aila.org",
            NewArticle,
        )
        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article.description, "ICE's detention expansion meets resistance")
        self.assertNotEqual(article.description.lower(), "national")
