import os

from django.http import HttpRequest


def google_analytics_account(_: HttpRequest) -> dict[str, str]:
    """Expose the GA_ACCOUNT env variable to templates when set."""
    account = os.environ.get('GA_ACCOUNT')
    if account:
        return {'GA_ACCOUNT': account.strip()}
    return {'GA_ACCOUNT': ''}
