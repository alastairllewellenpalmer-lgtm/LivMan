"""
WSGI config for horse_management project.
"""

import os
import sys
import json
import traceback
import importlib
from pathlib import Path

# Ensure the horse_management/ directory is on sys.path so that
# `core`, `billing`, `health`, etc. resolve to the correct inner
# packages rather than any stale repo-root duplicates.
_project_dir = str(Path(__file__).resolve().parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horse_management.settings')

# Try to boot Django; capture the error if it fails
_django_app = None
_boot_error = None
try:
    from django.core.wsgi import get_wsgi_application
    _django_app = get_wsgi_application()
except Exception:
    _boot_error = traceback.format_exc()


def application(environ, start_response):
    """WSGI entrypoint with diagnostic path interceptors."""
    path = environ.get('PATH_INFO', '')

    # Diagnostic endpoint — always works, even if Django failed to boot
    if path == '/_debug_paths/':
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '?')
        try:
            mod = importlib.import_module(settings_module)
            settings_file = getattr(mod, '__file__', '?')
            base_dir = str(getattr(mod, 'BASE_DIR', '?'))
            root_urlconf = getattr(mod, 'ROOT_URLCONF', '?')
        except Exception as exc:
            settings_file = f'import error: {exc}'
            base_dir = '?'
            root_urlconf = '?'

        body = json.dumps({
            'django_booted': _django_app is not None,
            'boot_error': _boot_error,
            'sys_path': sys.path[:10],
            'cwd': os.getcwd(),
            'settings_module': settings_module,
            'settings_file': settings_file,
            'BASE_DIR': base_dir,
            'ROOT_URLCONF': root_urlconf,
            'wsgi_file': __file__,
        }, indent=2).encode()

        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ])
        return [body]

    # If Django failed to boot, return the error for any other path
    if _django_app is None:
        body = json.dumps({
            'error': 'Django failed to start',
            'traceback': _boot_error,
        }, indent=2).encode()
        start_response('500 Internal Server Error', [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ])
        return [body]

    return _django_app(environ, start_response)


app = application
