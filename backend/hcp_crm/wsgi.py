"""
WSGI entry-point for hcp_crm.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hcp_crm.settings")
application = get_wsgi_application()
