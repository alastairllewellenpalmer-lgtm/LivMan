"""
WSGI config for horse_management project.
"""

import os
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horse_management.settings')

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception:
    error_text = traceback.format_exc()
    print(f"WSGI STARTUP ERROR:\n{error_text}")

    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Django failed to start:\n\n{error_text}".encode()]

app = application
