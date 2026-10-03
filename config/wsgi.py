import os

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# WhiteNoise serves the collected static files and the uploaded school logos
# straight from the WSGI layer, so gunicorn does not need a separate web server
# for them. In development Django's own static handling is used instead.
application = WhiteNoise(application, root=settings.STATIC_ROOT, prefix="static/")
application.add_files(settings.MEDIA_ROOT, prefix="media/")
