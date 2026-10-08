"""Entrada da API na Vercel.

A Vercel procura um `app` ASGI em api/index.py. O codigo da aplicacao continua em APP/;
este arquivo so o expoe.
"""

from APP.main import app  # noqa: F401
