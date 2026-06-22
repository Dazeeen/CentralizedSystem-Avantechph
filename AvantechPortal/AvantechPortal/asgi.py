"""Backward-compatible entrypoint for the project's WSGI deployment."""

from .wsgi import application

__all__ = ['application']
