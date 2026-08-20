"""Central slowapi limiter instance.

Imported by main.py (to register with the app) and by individual routers
(to apply per-endpoint limits). Keeping it in its own module avoids circular
imports: main.py imports routers which import the limiter — fine as long as
the limiter itself doesn't import from main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
