"""Tests for the nodon_wire_pilot climate module."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import (
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.select import SERVICE_SELECT_OPTION
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import CoreState, Event, EventStateChangedData, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.nodon_wire_pilot.climate import (
    NodonWirePilotClimate,
    PLATFORM_SCHEMA_COMMON,
    _async_setup_config,
    async_setup_entry,
    async_setup_platform,
)
from custom_components.nodon_wire_pilot.const import (
    CONF_ADDITIONAL_MODES,
    CONF_HEATER,
    CONF_SENSOR,
    DOMAIN,
    PLATFORMS,
    PRESET_COMFORT_1,
    PRESET_COMFORT_2,
    VALUE_COMFORT,
    VALUE_COMFORT_1,
    VALUE_COMFORT_2,
    VALUE_ECO,
    VALUE_FROST,
    VALUE_OFF,
)


# Test constants
WIRE_PILOT_ENTITY_ID = "select.heater_living_room"
SENSOR_ENTITY_ID = "sensor.temperature_living_room"
UNIQUE_ID = "nodon_test_unique_id"
ENTRY_ID = "test_entry_id"
DEVICE_ID = "device_123"


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
    entity.entity_id = WIRE_PILOT_ENTITY_ID
    entity.device_id = DEVICE_ID
    entity.has_entity_name = True
    return entity


@pytest.fixture
def mock_sensor_entity() -> MagicMock:
    """Create a mock sensor entity."""
    entity = MagicMock(spec=er.RegistryEntry)
    entity.entity_id = SENSOR_ENTITY_ID
    entity.device_id = DEVICE_ID
    return entity


@pytest.fixture
def mock_device() -> MagicMock:
    """Create a mock device."""
    device = MagicMock(spec=dr.DeviceEntry)
    device.id = DEVICE_ID
    device.connections = {("mac", "aa:bb:cc:dd:ee:ff")}
    device.identifiers = {("nodon_wire_pilot", DEVICE_ID)}
    return device


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


@pytest.fixture
def heater_state_factory():
    """Factory for creating heater states with different values."""

    def _factory(value: str) -> MagicMock:
        state = MagicMock(spec=State)
        state.entity_id = WIRE_PILOT_ENTITY_ID
        state.state = value
        return state

    return _factory


@pytest.fixture
def sensor_state_factory():
    """Factory for creating sensor states with different values."""

    def _factory(value: str | float | None) -> MagicMock:
        state = MagicMock(spec=State)
        state.entity_id = SENSOR_ENTITY_ID
        state.state = value
        return state

    return _factory


@pytest.fixture
def climate_entity_factory(
    mock_hass: MagicMock,
    mock_entity_registry: MagicMock,
    mock_device_registry: MagicMock,
    mock_heater_entity: MagicMock,
    mock_device: MagicMock,
):
    """Factory for creating NodonWirePilotClimate instances."""

    def _factory(
        name: str | None = "Test Climate",
        wire_pilot_entity_id: str = WIRE_PILOT_ENTITY_ID,
        sensor_entity_id: str | None = SENSOR_ENTITY_ID,
        additional_modes: bool = False,
        unique_id: str | None = UNIQUE_ID,
        heater_state_value: str = VALUE_COMFORT,
        sensor_state_value: str | float | None = "21.5",
    ) -> NodonWirePilotClimate:
        mock_entity_registry.async_get.side_effect = lambda eid: (
            mock_heater_entity if eid == wire_pilot_entity_id else mock_sensor_entity
        )

        # Use a dict to store state values that can be overridden by tests
        state_values = {
            wire_pilot_entity_id: heater_state_value,
            sensor_entity_id: sensor_state_value,
        }

        def get_state(eid):
            if eid in state_values:
                return MagicMock(spec=State, entity_id=eid, state=state_values[eid])
            return None

        mock_hass.states.get.side_effect = get_state

        entity = NodonWirePilotClimate(
            hass=mock_hass,
            name=name,
            wire_pilot_entity_id=wire_pilot_entity_id,
            sensor_entity_id=sensor_entity_id,
            additional_modes=additional_modes,
            unique_id=unique_id,
        )
        entity.hass = mock_hass
        # Store state_values on entity for test access
        entity._test_state_values = state_values
        return entity

    return _factory


class TestPlatformSchema:
    """Tests for PLATFORM_SCHEMA_COMMON."""

    def test_schema_valid_minimal_config(self) -> None:
        """Test schema with minimal required config."""
        config = {CONF_HEATER: WIRE_PILOT_ENTITY_ID}
        result = PLATFORM_SCHEMA_COMMON(config)
        assert result[CONF_HEATER] == WIRE_PILOT_ENTITY_ID
        assert result[CONF_ADDITIONAL_MODES] is False

    def test_schema_valid_full_config(self) -> None:
        """Test schema with all optional config."""
        config = {
            CONF_HEATER: WIRE_PILOT_ENTITY_ID,
            CONF_SENSOR: SENSOR_ENTITY_ID,
            CONF_ADDITIONAL_MODES: True,
        }
        result = PLATFORM_SCHEMA_COMMON(config)
        assert result[CONF_HEATER] == WIRE_PILOT_ENTITY_ID
        assert result[CONF_SENSOR] == SENSOR_ENTITY_ID
        assert result[CONF_ADDITIONAL_MODES] is True

    def test_schema_missing_required_heater(self) -> None:
        """Test schema raises error when heater is missing."""
        config = {CONF_SENSOR: SENSOR_ENTITY_ID}
        with pytest.raises(Exception):  # voluptuous.Invalid
            PLATFORM_SCHEMA_COMMON(config)


class TestNodonWirePilotClimateInitialization:
    """Tests for NodonWirePilotClimate initialization."""

    def test_init_with_all_params(
        self,
        climate_entity_factory,
        mock_hass: MagicMock,
        mock_heater_entity: MagicMock,
        mock_device: MagicMock,
    ) -> None:
        """Test initialization with all parameters."""
        entity = climate_entity_factory(
            name="Living Room",
            wire_pilot_entity_id=WIRE_PILOT_ENTITY_ID,
            sensor_entity_id=SENSOR_ENTITY_ID,
            additional_modes=True,
            unique_id=UNIQUE_ID,
        )

        assert entity.wire_pilot_entity_id == WIRE_PILOT_ENTITY_ID
        assert entity.sensor_entity_id == SENSOR_ENTITY_ID
        assert entity.additional_modes is True
        assert entity._attr_name == "Living Room"
        assert entity._attr_unique_id == UNIQUE_ID
        assert entity._attr_translation_key == "nodon_wire_pilot"
        assert entity._attr_should_poll is False

    def test_init_without_sensor(
        self,
        climate_entity_factory,
        mock_hass: MagicMock,
        mock_heater_entity: MagicMock,
    ) -> None:
        """Test initialization without sensor entity."""
        entity = climate_entity_factory(sensor_entity_id=None)

        assert entity.sensor_entity_id is None
        assert entity.additional_modes is False

    def test_init_without_name(
        self,
        climate_entity_factory,
        mock_hass: MagicMock,
        mock_heater_entity: MagicMock,
    ) -> None:
        """Test initialization without name."""
        entity = climate_entity_factory(name=None)

        # When name is None, _attr_name is not set (stays as default None from ClimateEntity)
        assert getattr(entity, "_attr_name", None) is None
        assert entity._attr_has_entity_name is True

    def test_init_generates_unique_id_when_none(
        self,
        climate_entity_factory,
        mock_hass: MagicMock,
        mock_heater_entity: MagicMock,
    ) -> None:
        """Test unique_id is generated when not provided."""
        entity = climate_entity_factory(unique_id=None)

        # Unique ID is generated from wire_pilot_entity_id
        assert entity._attr_unique_id == f"{DOMAIN}_{WIRE_PILOT_ENTITY_ID}"

    def test_init_device_info_from_heater(
        self,
        climate_entity_factory,
        mock_device: MagicMock,
    ) -> None:
        """Test device info is set from heater entity."""
        entity = climate_entity_factory()

        assert entity._attr_device_info is not None
        # DeviceInfo is a dict-like object, check its contents
        assert entity._attr_device_info.get("connections") == mock_device.connections
        assert entity._attr_device_info.get("identifiers") == mock_device.identifiers

    def test_init_device_info_none_when_no_device(
        self,
        climate_entity_factory,
        mock_heater_entity: MagicMock,
        mock_device_registry: MagicMock,
    ) -> None:
        """Test device info is None when heater has no device_id."""
        mock_heater_entity.device_id = None
        mock_device_registry.async_get.return_value = None

        entity = climate_entity_factory()

        assert entity._attr_device_info is None


class TestSupportedFeatures:
    """Tests for supported_features property."""

    def test_supported_features(self, climate_entity_factory) -> None:
        """Test supported features include preset and turn on/off."""
        entity = climate_entity_factory()

        features = entity.supported_features
        assert ClimateEntityFeature.PRESET_MODE in features
        assert ClimateEntityFeature.TURN_OFF in features
        assert ClimateEntityFeature.TURN_ON in features
        assert ClimateEntityFeature.TARGET_TEMPERATURE not in features


class TestTemperatureUnit:
    """Tests for temperature_unit property."""

    def test_temperature_unit(self, climate_entity_factory) -> None:
        """Test temperature unit is Celsius."""
        entity = climate_entity_factory()
        assert entity.temperature_unit == UnitOfTemperature.CELSIUS


class TestCurrentTemperature:
    """Tests for current_temperature property."""

    def test_current_temperature_returns_sensor_value(
        self, climate_entity_factory, sensor_state_factory
    ) -> None:
        """Test current_temperature returns sensor value."""
        entity = climate_entity_factory()
        entity._cur_temperature = 21.5

        assert entity.current_temperature == 21.5

    def test_current_temperature_none_when_no_sensor(self, climate_entity_factory) -> None:
        """Test current_temperature is None when no sensor configured."""
        entity = climate_entity_factory(sensor_entity_id=None)
        entity._cur_temperature = None

        assert entity.current_temperature is None


class TestHeaterValue:
    """Tests for heater_value property."""

    def test_heater_value_returns_state(
        self, climate_entity_factory, heater_state_factory, mock_hass: MagicMock
    ) -> None:
        """Test heater_value returns heater state."""
        entity = climate_entity_factory()
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = VALUE_COMFORT

        assert entity.heater_value == VALUE_COMFORT

    def test_heater_value_none_when_no_state(
        self, climate_entity_factory, mock_hass: MagicMock
    ) -> None:
        """Test heater_value returns None when state is None."""
        entity = climate_entity_factory()
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = None

        assert entity.heater_value is None


class TestPresetModes:
    """Tests for preset_modes property."""

    def test_preset_modes_without_additional_modes(self, climate_entity_factory) -> None:
        """Test preset modes without additional modes."""
        entity = climate_entity_factory(additional_modes=False)

        modes = entity.preset_modes
        assert PRESET_COMFORT in modes
        assert PRESET_ECO in modes
        assert PRESET_AWAY in modes
        assert PRESET_NONE in modes
        assert PRESET_COMFORT_1 not in modes
        assert PRESET_COMFORT_2 not in modes
        assert len(modes) == 4

    def test_preset_modes_with_additional_modes(self, climate_entity_factory) -> None:
        """Test preset modes with additional modes."""
        entity = climate_entity_factory(additional_modes=True)

        modes = entity.preset_modes
        assert PRESET_COMFORT in modes
        assert PRESET_COMFORT_1 in modes
        assert PRESET_COMFORT_2 in modes
        assert PRESET_ECO in modes
        assert PRESET_AWAY in modes
        assert PRESET_NONE in modes
        assert len(modes) == 6


class TestPresetMode:
    """Tests for preset_mode property."""

    @pytest.mark.parametrize(
        "heater_value,expected_preset",
        [
            (VALUE_OFF, PRESET_NONE),
            (VALUE_FROST, PRESET_AWAY),
            (VALUE_ECO, PRESET_ECO),
            (VALUE_COMFORT, PRESET_COMFORT),
            # VALUE_COMFORT_1 and VALUE_COMFORT_2 map to PRESET_COMFORT when additional_modes is False
            # They are tested in separate test methods
        ],
    )
    def test_preset_mode_mapping_without_additional(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
        heater_value: str,
        expected_preset: str,
    ) -> None:
        """Test preset mode mapping for standard modes."""
        entity = climate_entity_factory(additional_modes=False)
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = heater_value

        assert entity.preset_mode == expected_preset

    def test_preset_mode_comfort_1_maps_to_comfort_without_additional(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
    ) -> None:
        """Test Comfort -1 maps to Comfort when additional_modes is False."""
        entity = climate_entity_factory(additional_modes=False)
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = VALUE_COMFORT_1

        assert entity.preset_mode == PRESET_COMFORT

    def test_preset_mode_comfort_2_maps_to_comfort_without_additional(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
    ) -> None:
        """Test Comfort -2 maps to Comfort when additional_modes is False."""
        entity = climate_entity_factory(additional_modes=False)
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = VALUE_COMFORT_2

        assert entity.preset_mode == PRESET_COMFORT

    def test_preset_mode_comfort_1_maps_to_comfort_1_with_additional(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
    ) -> None:
        """Test Comfort -1 maps to Comfort -1 when additional_modes is True."""
        entity = climate_entity_factory(additional_modes=True)
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = VALUE_COMFORT_1

        assert entity.preset_mode == PRESET_COMFORT_1

    def test_preset_mode_comfort_2_maps_to_comfort_2_with_additional(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
    ) -> None:
        """Test Comfort -2 maps to Comfort -2 when additional_modes is True."""
        entity = climate_entity_factory(additional_modes=True)
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = VALUE_COMFORT_2

        assert entity.preset_mode == PRESET_COMFORT_2

    def test_preset_mode_none_when_heater_value_none(
        self, climate_entity_factory, mock_hass: MagicMock
    ) -> None:
        """Test preset_mode returns None when heater_value is None."""
        entity = climate_entity_factory()
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = None

        assert entity.preset_mode is None

    def test_preset_mode_unknown_value_logs_warning(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test preset_mode logs warning for unknown value."""
        entity = climate_entity_factory()
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = "unknown_value"

        result = entity.preset_mode

        assert result is None
        assert "Unexpected value 'unknown_value'" in caplog.text


class TestAsyncSetPresetMode:
    """Tests for async_set_preset_mode method."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "preset_mode,expected_value",
        [
            (PRESET_AWAY, VALUE_FROST),
            (PRESET_ECO, VALUE_ECO),
            (PRESET_COMFORT, VALUE_COMFORT),
            (PRESET_NONE, VALUE_OFF),
        ],
    )
    async def test_set_preset_mode_standard_modes(
        self,
        climate_entity_factory,
        preset_mode: str,
        expected_value: str,
    ) -> None:
        """Test setting standard preset modes."""
        entity = climate_entity_factory()
        entity._async_select_wire_pilot_mode = AsyncMock()

        await entity.async_set_preset_mode(preset_mode)

        entity._async_select_wire_pilot_mode.assert_called_once_with(expected_value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "preset_mode,expected_value",
        [
            (PRESET_COMFORT_1, VALUE_COMFORT_1),
            (PRESET_COMFORT_2, VALUE_COMFORT_2),
        ],
    )
    async def test_set_preset_mode_additional_modes(
        self,
        climate_entity_factory,
        preset_mode: str,
        expected_value: str,
    ) -> None:
        """Test setting additional preset modes when enabled."""
        entity = climate_entity_factory(additional_modes=True)
        entity._async_select_wire_pilot_mode = AsyncMock()

        await entity.async_set_preset_mode(preset_mode)

        entity._async_select_wire_pilot_mode.assert_called_once_with(expected_value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "preset_mode",
        [PRESET_COMFORT_1, PRESET_COMFORT_2],
    )
    async def test_set_preset_mode_additional_modes_raises_when_disabled(
        self,
        climate_entity_factory,
        preset_mode: str,
    ) -> None:
        """Test setting additional preset modes raises when disabled."""
        entity = climate_entity_factory(additional_modes=False)

        with pytest.raises(ValueError, match=f"Unsupported preset mode: {preset_mode}"):
            await entity.async_set_preset_mode(preset_mode)

    @pytest.mark.asyncio
    async def test_set_preset_mode_invalid_raises(
        self, climate_entity_factory
    ) -> None:
        """Test setting invalid preset mode raises ValueError."""
        entity = climate_entity_factory()

        with pytest.raises(ValueError, match="Unsupported preset mode: invalid"):
            await entity.async_set_preset_mode("invalid")


class TestHVACModes:
    """Tests for hvac_modes property."""

    def test_hvac_modes(self, climate_entity_factory) -> None:
        """Test hvac modes are HEAT and OFF."""
        entity = climate_entity_factory()

        modes = entity.hvac_modes
        assert HVACMode.HEAT in modes
        assert HVACMode.OFF in modes
        assert len(modes) == 2


class TestAsyncSetHVACMode:
    """Tests for async_set_hvac_mode method."""

    @pytest.mark.asyncio
    async def test_set_hvac_mode_heat(
        self, climate_entity_factory
    ) -> None:
        """Test setting HVAC mode to HEAT."""
        entity = climate_entity_factory()
        entity._async_select_wire_pilot_mode = AsyncMock()

        await entity.async_set_hvac_mode(HVACMode.HEAT)

        entity._async_select_wire_pilot_mode.assert_called_once_with(VALUE_COMFORT)

    @pytest.mark.asyncio
    async def test_set_hvac_mode_off(
        self, climate_entity_factory
    ) -> None:
        """Test setting HVAC mode to OFF."""
        entity = climate_entity_factory()
        entity._async_select_wire_pilot_mode = AsyncMock()

        await entity.async_set_hvac_mode(HVACMode.OFF)

        entity._async_select_wire_pilot_mode.assert_called_once_with(VALUE_OFF)

    @pytest.mark.asyncio
    async def test_set_hvac_mode_invalid_raises(
        self, climate_entity_factory
    ) -> None:
        """Test setting invalid HVAC mode raises ValueError."""
        entity = climate_entity_factory()

        with pytest.raises(ValueError, match="Unsupported HVAC mode: cool"):
            await entity.async_set_hvac_mode(HVACMode.COOL)


class TestHVACMode:
    """Tests for hvac_mode property."""

    @pytest.mark.parametrize(
        "heater_value,expected_mode",
        [
            (VALUE_OFF, HVACMode.OFF),
            (VALUE_FROST, HVACMode.HEAT),
            (VALUE_ECO, HVACMode.HEAT),
            (VALUE_COMFORT, HVACMode.HEAT),
            (VALUE_COMFORT_1, HVACMode.HEAT),
            (VALUE_COMFORT_2, HVACMode.HEAT),
        ],
    )
    def test_hvac_mode_mapping(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
        heater_value: str,
        expected_mode: HVACMode,
    ) -> None:
        """Test HVAC mode mapping from heater values."""
        entity = climate_entity_factory()
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = heater_value

        assert entity.hvac_mode == expected_mode

    def test_hvac_mode_none_when_heater_value_none(
        self, climate_entity_factory, mock_hass: MagicMock
    ) -> None:
        """Test hvac_mode returns None when heater_value is None."""
        entity = climate_entity_factory()
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = None

        assert entity.hvac_mode is None

    def test_hvac_mode_unknown_value_logs_warning(
        self,
        climate_entity_factory,
        heater_state_factory,
        mock_hass: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test hvac_mode logs warning for unknown value."""
        entity = climate_entity_factory()
        entity._test_state_values[WIRE_PILOT_ENTITY_ID] = "unknown_value"

        result = entity.hvac_mode

        assert result is None
        assert "Unexpected value 'unknown_value'" in caplog.text


class TestAsyncSensorChanged:
    """Tests for _async_sensor_changed callback."""

    @pytest.mark.asyncio
    async def test_sensor_changed_updates_temperature(
        self, climate_entity_factory, sensor_state_factory
    ) -> None:
        """Test sensor changed updates temperature."""
        entity = climate_entity_factory()
        entity.async_write_ha_state = MagicMock()
        new_state = sensor_state_factory("22.0")

        event = MagicMock(spec=Event)
        event.data = {"new_state": new_state}

        await entity._async_sensor_changed(event)

        assert entity._cur_temperature == 22.0
        entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_sensor_changed_none_state(
        self, climate_entity_factory
    ) -> None:
        """Test sensor changed with None state."""
        entity = climate_entity_factory()
        entity.async_write_ha_state = MagicMock()

        event = MagicMock(spec=Event)
        event.data = {"new_state": None}

        await entity._async_sensor_changed(event)

        assert entity._cur_temperature is None
        entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_sensor_changed_unavailable_state(
        self, climate_entity_factory, sensor_state_factory
    ) -> None:
        """Test sensor changed with unavailable state."""
        entity = climate_entity_factory()
        entity.async_write_ha_state = MagicMock()
        new_state = sensor_state_factory(STATE_UNAVAILABLE)

        event = MagicMock(spec=Event)
        event.data = {"new_state": new_state}

        await entity._async_sensor_changed(event)

        assert entity._cur_temperature is None
        entity.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_sensor_changed_unknown_state(
        self, climate_entity_factory, sensor_state_factory
    ) -> None:
        """Test sensor changed with unknown state."""
        entity = climate_entity_factory()
        entity.async_write_ha_state = MagicMock()
        new_state = sensor_state_factory(STATE_UNKNOWN)

        event = MagicMock(spec=Event)
        event.data = {"new_state": new_state}

        await entity._async_sensor_changed(event)

        assert entity._cur_temperature is None
        entity.async_write_ha_state.assert_called_once()


class TestAsyncHeaterChanged:
    """Tests for _async_heater_changed callback."""

    def test_heater_changed_updates_state(
        self, climate_entity_factory, heater_state_factory
    ) -> None:
        """Test heater changed triggers state update."""
        entity = climate_entity_factory()
        entity.async_write_ha_state = MagicMock()
        new_state = heater_state_factory(VALUE_ECO)

        event = MagicMock(spec=Event)
        event.data = {"new_state": new_state}

        entity._async_heater_changed(event)

        entity.async_write_ha_state.assert_called_once()

    def test_heater_changed_none_state(
        self, climate_entity_factory
    ) -> None:
        """Test heater changed with None state does nothing."""
        entity = climate_entity_factory()
        entity.async_write_ha_state = MagicMock()

        event = MagicMock(spec=Event)
        event.data = {"new_state": None}

        entity._async_heater_changed(event)

        entity.async_write_ha_state.assert_not_called()


class TestAsyncUpdateTemp:
    """Tests for _async_update_temp callback."""

    def test_update_temp_valid_float(
        self, climate_entity_factory, sensor_state_factory
    ) -> None:
        """Test updating temperature with valid float."""
        entity = climate_entity_factory()
        state = sensor_state_factory("21.5")

        entity._async_update_temp(state)

        assert entity._cur_temperature == 21.5

    def test_update_temp_valid_int(
        self, climate_entity_factory, sensor_state_factory
    ) -> None:
        """Test updating temperature with valid int."""
        entity = climate_entity_factory()
        state = sensor_state_factory("22")

        entity._async_update_temp(state)

        assert entity._cur_temperature == 22.0

    def test_update_temp_invalid_state_logs_error(
        self, climate_entity_factory, sensor_state_factory, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test updating temperature with invalid state logs error."""
        entity = climate_entity_factory()
        state = sensor_state_factory("invalid")

        entity._async_update_temp(state)

        assert entity._cur_temperature is None
        assert "Unable to update from temperature sensor" in caplog.text

    def test_update_temp_none_state_logs_error(
        self, climate_entity_factory, sensor_state_factory, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test updating temperature with invalid state logs error."""
        entity = climate_entity_factory()
        state = sensor_state_factory("")

        entity._async_update_temp(state)

        assert entity._cur_temperature is None
        assert "Unable to update from temperature sensor" in caplog.text

    def test_update_temp_nan_logs_error(
        self, climate_entity_factory, sensor_state_factory, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test updating temperature with NaN logs error."""
        entity = climate_entity_factory()
        state = sensor_state_factory(float("nan"))

        entity._async_update_temp(state)

        assert entity._cur_temperature is None
        assert "Unable to update from temperature sensor" in caplog.text

    def test_update_temp_infinity_logs_error(
        self, climate_entity_factory, sensor_state_factory, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test updating temperature with infinity logs error."""
        entity = climate_entity_factory()
        state = sensor_state_factory(float("inf"))

        entity._async_update_temp(state)

        assert entity._cur_temperature is None
        assert "Unable to update from temperature sensor" in caplog.text


class TestAsyncSelectWirePilotMode:
    """Tests for _async_select_wire_pilot_mode method."""

    @pytest.mark.asyncio
    async def test_select_wire_pilot_mode_calls_service(
        self, climate_entity_factory, mock_hass: MagicMock
    ) -> None:
        """Test _async_select_wire_pilot_mode calls select.select_option service."""
        entity = climate_entity_factory()

        await entity._async_select_wire_pilot_mode(VALUE_COMFORT)

        mock_hass.services.async_call.assert_called_once_with(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: WIRE_PILOT_ENTITY_ID, "option": VALUE_COMFORT},
            blocking=True,
        )

    @pytest.mark.asyncio
    async def test_select_wire_pilot_mode_all_modes(
        self, climate_entity_factory, mock_hass: MagicMock
    ) -> None:
        """Test _async_select_wire_pilot_mode with all mode values."""
        entity = climate_entity_factory()

        for value in [VALUE_OFF, VALUE_FROST, VALUE_ECO, VALUE_COMFORT, VALUE_COMFORT_1, VALUE_COMFORT_2]:
            mock_hass.services.async_call.reset_mock()
            await entity._async_select_wire_pilot_mode(value)
            mock_hass.services.async_call.assert_called_once_with(
                SELECT_DOMAIN,
                SERVICE_SELECT_OPTION,
                {ATTR_ENTITY_ID: WIRE_PILOT_ENTITY_ID, "option": value},
                blocking=True,
            )


class TestAsyncAddedToHass:
    """Tests for async_added_to_hass method."""

    @pytest.mark.asyncio
    async def test_added_to_hass_registers_listeners(
        self, climate_entity_factory, mock_hass: MagicMock
    ) -> None:
        """Test async_added_to_hass registers state change listeners."""
        # Use pytest-homeassistant-custom-component for proper HA mocking
        pass

    @pytest.mark.asyncio
    async def test_added_to_hass_sensor_only_when_configured(
        self, climate_entity_factory, mock_hass: MagicMock
    ) -> None:
        """Test sensor listener only registered when sensor configured."""
        # Use pytest-homeassistant-custom-component for proper HA mocking
        pass


class TestAsyncSetupConfig:
    """Tests for _async_setup_config function."""

    @pytest.mark.asyncio
    async def test_async_setup_config_creates_entity(
        self, mock_hass: MagicMock, mock_entity_registry: MagicMock
    ) -> None:
        """Test _async_setup_config creates and adds entity."""
        mock_entity_registry.async_get.return_value = MagicMock(
            entity_id=WIRE_PILOT_ENTITY_ID, device_id=DEVICE_ID, has_entity_name=True
        )
        mock_hass.states.get.return_value = MagicMock(
            entity_id=WIRE_PILOT_ENTITY_ID, state=VALUE_COMFORT
        )
        async_add_entities = MagicMock()

        config = {
            CONF_HEATER: WIRE_PILOT_ENTITY_ID,
            CONF_SENSOR: SENSOR_ENTITY_ID,
            CONF_ADDITIONAL_MODES: False,
        }

        await _async_setup_config(
            mock_hass, config, UNIQUE_ID, async_add_entities
        )

        async_add_entities.assert_called_once()
        args = async_add_entities.call_args[0][0]
        assert len(args) == 1
        assert isinstance(args[0], NodonWirePilotClimate)


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self, mock_hass: MagicMock
    ) -> None:
        """Test async_setup_entry calls _async_setup_config."""
        config_entry = MagicMock()
        config_entry.entry_id = ENTRY_ID
        config_entry.options = {CONF_HEATER: WIRE_PILOT_ENTITY_ID}

        with patch("custom_components.nodon_wire_pilot.climate._async_setup_config") as mock_setup:
            await async_setup_entry(mock_hass, config_entry, MagicMock())

        mock_setup.assert_called_once()


class TestAsyncSetupPlatform:
    """Tests for async_setup_platform function."""

    @pytest.mark.asyncio
    async def test_async_setup_platform(
        self, mock_hass: MagicMock
    ) -> None:
        """Test async_setup_platform calls _async_setup_config."""
        config = {CONF_HEATER: WIRE_PILOT_ENTITY_ID}
        async_add_entities = MagicMock()

        with patch("custom_components.nodon_wire_pilot.climate._async_setup_config") as mock_setup:
            with patch("custom_components.nodon_wire_pilot.climate.async_setup_reload_service"):
                await async_setup_platform(mock_hass, config, async_add_entities)

        mock_setup.assert_called_once()