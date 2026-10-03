import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    """Static URL with a version query taken from the file's modified time.

    Browsers cache CSS and JS aggressively; changing the query string forces a
    fresh fetch every time the file changes.
    """
    url = static(path)
    absolute = finders.find(path)
    if absolute:
        return f"{url}?v={int(os.path.getmtime(absolute))}"
    return url
