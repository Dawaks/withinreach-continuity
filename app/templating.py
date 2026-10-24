"""Shared Jinja2 templates instance used across all page routes."""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
