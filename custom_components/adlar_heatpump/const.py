"""Constants for Adlar Heatpump integration.

The register map lives in registers.py.
"""

DOMAIN = "adlar_heatpump"
DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 60

CONF_SLAVE = "slave"
# Seconds between reads of the slow tier (P/L parameters, limits, version info)
CONF_SLOW_INTERVAL = "slow_interval"
DEFAULT_SLOW_INTERVAL = 600
# Expert mode: P/L installer parameters become writable number/select entities
CONF_EXPERT_MODE = "expert_mode"

DEVICE_NAME = "Adlar Aurora II Heatpump"
