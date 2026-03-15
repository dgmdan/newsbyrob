from django import template

from bs4 import BeautifulSoup

register = template.Library()


@register.filter
def article_snippet(description: str, limit: int = 300) -> str:
    if not description:
        return ""

    text = BeautifulSoup(description, "html.parser").get_text(" ", strip=True)
    if len(text) <= limit:
        return text

    snippet = text[:limit]
    if not snippet[-1].isspace():
        snippet = snippet.rstrip()
        while snippet and not snippet[-1].isspace():
            snippet = snippet[:-1]
    snippet = snippet.rstrip()
    return f"{snippet}..."
