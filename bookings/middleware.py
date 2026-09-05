from django.conf import settings


class ForceDefaultLanguageMiddleware:
    """
    Django's LocaleMiddleware picks a language from the browser's
    Accept-Language header whenever the visitor hasn't explicitly chosen one
    yet, which means most visitors would see English (or whatever their OS
    is set to) instead of the site's intended Hebrew default. Stripping the
    header for visitors with no saved language preference makes
    LocaleMiddleware fall through to settings.LANGUAGE_CODE (Hebrew)
    instead. Once someone uses the language switcher, Django's set_language
    view stores their explicit choice in a cookie, and this middleware
    leaves it alone from then on.

    Must run before LocaleMiddleware (which reads the Accept-Language
    header).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            request.META.pop('HTTP_ACCEPT_LANGUAGE', None)
        return self.get_response(request)
