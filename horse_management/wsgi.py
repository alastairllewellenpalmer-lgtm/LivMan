"""
WSGI config for horse_management project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horse_management.settings')

application = get_wsgi_application()
app = application
