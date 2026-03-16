import os

from django.http import HttpResponsePermanentRedirect


class WwwRedirectMiddleware:
    """Redirect www.newsbyrob.com requests to the canonical host."""

    def __init__(self, get_response):
        self._get_response = get_response
        canonical = os.environ.get('CANONICAL_HOST', 'newsbyrob.com').strip().lower()
        self.canonical_host = canonical or 'newsbyrob.com'
        self.www_host = f'www.{self.canonical_host}'

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        if host == self.www_host:
            scheme = 'https' if request.is_secure() else request.scheme
            target = f'{scheme}://{self.canonical_host}{request.get_full_path()}'
            return HttpResponsePermanentRedirect(target)
        return self._get_response(request)
