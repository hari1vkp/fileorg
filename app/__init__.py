"""fileorg - a small, safe file organiser for Windows and Linux.

The desktop application lives in :mod:`app.application`; the command line
interface lives in :mod:`app.cli`. Both are built on the same core planner,
mover and journal code in :mod:`app.core`.
"""

from app.core.constants import APP_VERSION as __version__

__all__ = ["__version__"]
