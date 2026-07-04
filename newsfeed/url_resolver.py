from dataclasses import dataclass
from urllib.parse import urljoin

import requests

from scripts.support import logger


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:152.0) Gecko/20100101 Firefox/152.0"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}
MAX_REDIRECT_HOPS = 10


@dataclass(frozen=True)
class ResolvedURL:
    url: str
    rate_limited: bool = False


def resolve_final_url(url: str | None, timeout: int = 10) -> ResolvedURL:
    if not url:
        return ResolvedURL(url="")

    normalized = url.strip()
    if not normalized:
        return ResolvedURL(url="")

    if not normalized.startswith(("http://", "https://")):
        return ResolvedURL(url=normalized)

    current_url = normalized
    seen_urls = {normalized}

    try:
        for _ in range(MAX_REDIRECT_HOPS):
            with requests.get(
                current_url,
                headers=REQUEST_HEADERS,
                allow_redirects=False,
                timeout=timeout,
                stream=True,
            ) as response:
                if response.status_code == 429:
                    logger.warning(f"Rate limited while resolving {normalized}")
                    return ResolvedURL(url=normalized, rate_limited=True)

                if response.is_redirect or response.is_permanent_redirect:
                    location = response.headers.get("Location")
                    if not location:
                        return ResolvedURL(url=current_url)
                    next_url = urljoin(current_url, location.strip())
                    if not next_url or next_url in seen_urls:
                        logger.warning(f"Redirect loop detected while resolving {normalized}")
                        return ResolvedURL(url=current_url)
                    seen_urls.add(next_url)
                    current_url = next_url
                    continue

                return ResolvedURL(url=response.url or current_url)

        logger.warning(f"Maximum redirect hops reached while resolving {normalized}")
        return ResolvedURL(url=current_url)
    except Exception as exc:
        logger.debug(f"Unable to resolve final URL for {normalized}: {exc}")
        return ResolvedURL(url=normalized)
