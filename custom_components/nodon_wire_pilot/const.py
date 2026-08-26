"""Constants for the NodOn Wire Pilot integration."""

from homeassistant.const import Platform

DOMAIN = "nodon_wire_pilot"

PLATFORMS: list[Platform] = [Platform.CLIMATE]

# Configuration
CONF_HEATER = "heater"
CONF_SENSOR = "sensor"
CONF_ADDITIONAL_MODES = "additional_modes"

# Wire pilot values
VALUE_OFF = "off"
VALUE_FROST = "frost_protection"
VALUE_ECO = "eco"
VALUE_COMFORT_2 = "comfort_-2"
VALUE_COMFORT_1 = "comfort_-1"
VALUE_COMFORT = "comfort"

# Climate presets
PRESET_COMFORT_1 = "Comfort -1"
PRESET_COMFORT_2 = "Comfort -2"