"""
API v1 Router
=============

DEPRECATED: This file is deprecated. Use __init__.py instead.
The actual router is defined in __init__.py which imports from v1/ directly
(containing the full implementations, not stubs).

This file is kept for backwards compatibility only.
"""

# Re-export from __init__.py for backwards compatibility
from app.api.v1 import api_router

__all__ = ["api_router"]
