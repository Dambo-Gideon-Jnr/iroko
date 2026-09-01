import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
APP_ROOT = os.path.join(ROOT, "iroko-flask")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from app import app

# Vercel will import this module and use the exported `app` callable.
