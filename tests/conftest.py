"""Set default env vars before any test module imports.

Pytest loads conftest.py before test modules, so this runs before
`from config.settings import settings` is executed, which would
otherwise raise ValidationError due to missing required env vars.
"""
import os

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-default")
os.environ.setdefault("MYSQL_HOST", "127.0.0.1")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MYSQL_DB", "test")
