"""Lux fleet manager — backward compatibility re-export.

All generic fleet management lives in fleet_manager.py.
New code should import FleetManager from fleet_manager directly.
"""

from bootnode.core.chains.fleet_manager import FleetManager  # noqa: F401

# Backward compatibility alias
LuxFleetManager = FleetManager
