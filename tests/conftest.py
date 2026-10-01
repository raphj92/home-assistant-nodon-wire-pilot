"""pytest configuration and fixtures for nodon_wire_pilot tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import (
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CoreState, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.nodon_wire_pilot.const import (
    CONF_ADDITIONAL_MODES,
    CONF_HEATER,
    CONF_SENSOR,
    DOMAIN,
    PRESET_COMFORT_1 as CUSTOM_PRESET_COMFORT_1,
    PRESET_COMFORT_2 as CUSTOM_PRESET_COMFORT_2,
    VALUE_COMFORT,
    VALUE_COMFORT_1,
    VALUE_COMFORT_2,
    VALUE_ECO,
    VALUE_FROST,
    VALUE_OFF,
)


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.state = CoreState.running
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.bus = MagicMock()
    hass.bus.async_listen_once = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_reload = AsyncMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_entity_registry() -> MagicMock:
    """Create a mock entity registry."""
    registry = MagicMock(spec=er.EntityRegistry)
    registry.async_get = MagicMock()
    registry.async_update_entity = MagicMock()
    return registry


@pytest.fixture
def mock_device_registry() -> MagicMock:
    """Create a mock device registry."""
    registry = MagicMock(spec=dr.DeviceRegistry)
    registry.async_get = MagicMock()
    return registry


@pytest.fixture
def mock_heater_entity() -> MagicMock:
    """Create a mock heater entity."""
    entity = MagicMock(spec=er.RegistryEntry)
    entity.entity_id = "select.heater_living_room"
    entity.device_id = "device_123"
    entity.has_entity_name = True
    return entity


@pytest.fixture
def mock_sensor_entity() -> MagicMock:
    """Create a mock sensor entity."""
    entity = MagicMock(spec=er.RegistryEntry)
    entity.entity_id = "sensor.temperature_living_room"
    entity.device_id = "device_123"
    return entity


@pytest.fixture
def mock_device() -> MagicMock:
    """Create a mock device."""
    device = MagicMock(spec=dr.DeviceEntry)
    device.id = "device_123"
    device.connections = {("mac", "aa:bb:cc:dd:ee:ff")}
    device.identifiers = {("nodon_wire_pilot", "device_123")}
    return device


@pytest.fixture
def heater_state() -> MagicMock:
    """Create a mock heater state."""
    state = MagicMock(spec=State)
    state.entity_id = "select.heater_living_room"
    state.state = VALUE_COMFORT
    return state


@pytest.fixture
def sensor_state() -> MagicMock:
    """Create a mock sensor state."""
    state = MagicMock(spec=State)
    state.entity_id = "sensor.temperature_living_room"
    state.state = "21.5"
    return state


@pytest.fixture(autouse=True)
def mock_registries(
    mock_entity_registry: MagicMock,
    mock_device_registry: MagicMock,
    mock_heater_entity: MagicMock,
    mock_device: MagicMock,
) -> Generator[None, None, None]:
    """Mock the registries globally."""
    with (
        patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry),
        patch("homeassistant.helpers.device_registry.async_get", return_value=mock_device_registry),
    ):
        mock_entity_registry.async_get.return_value = mock_heater_entity
        mock_device_registry.async_get.return_value = mock_device
        yield


# Preset value constants for tests
PRESET_VALUES = {
    PRESET_NONE: VALUE_OFF,
    PRESET_AWAY: VALUE_FROST,
    PRESET_ECO: VALUE_ECO,
    PRESET_COMFORT: VALUE_COMFORT,
    CUSTOM_PRESET_COMFORT_1: VALUE_COMFORT_1,
    CUSTOM_PRESET_COMFORT_2: VALUE_COMFORT_2,
}

HVAC_MODE_VALUES = {
    "heat": VALUE_COMFORT,
    "off": VALUE_OFF,
}