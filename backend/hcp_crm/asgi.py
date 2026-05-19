"""
ASGI entry-point for hcp_crm.
Supports async-capable servers (Daphne, Uvicorn).
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hcp_crm.settings")
application = get_asgi_application()
