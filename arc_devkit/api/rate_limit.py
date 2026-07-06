"""Shared rate limiter — separate module so routes can import it without cycles."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Identifies requests by client IP
limiter = Limiter(key_func=get_remote_address)
