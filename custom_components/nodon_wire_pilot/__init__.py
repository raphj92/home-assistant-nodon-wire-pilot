"""Nodon wire pilot component."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import (
    async_remove_stale_devices_links_keep_entity_device,
)


from .const import CONF_HEATER, DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    # CONF_HEATER can be in data (initial setup) or options (migrated/updated)
    heater_entity_id = entry.data.get(CONF_HEATER) or entry.options.get(CONF_HEATER)
    if not heater_entity_id:
        raise ValueError(f"Missing {CONF_HEATER} in config entry")

    async_remove_stale_devices_links_keep_entity_device(
        hass,
        entry.entry_id,
        heater_entity_id,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)