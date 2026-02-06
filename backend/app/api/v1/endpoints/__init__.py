"""
DEPRECATED: This endpoints/ folder contains STUB implementations.
==================================================================

DO NOT USE THESE FILES!

The actual working implementations are in the parent folder (app/api/v1/):
- app/api/v1/auth.py (full JWT authentication)
- app/api/v1/agents.py (full agent management)
- app/api/v1/campaigns.py (full campaign management)
- app/api/v1/numbers.py (full number list management)
- app/api/v1/calls.py (full call management with WebSocket)
- app/api/v1/recordings.py (full recording management)
- etc.

This folder will be removed in a future version.
The stubs here were created during initial scaffolding and are not used.
"""

import warnings

warnings.warn(
    "The app.api.v1.endpoints module is deprecated. "
    "Use app.api.v1.* directly instead.",
    DeprecationWarning,
    stacklevel=2
)
