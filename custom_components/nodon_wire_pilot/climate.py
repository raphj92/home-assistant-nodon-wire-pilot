"""Platform for Nodon Wire Pilot."""
import logging
import math

import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_START,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import (
    CoreState,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
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

_LOGGER = logging.getLogger(__name__)

SELECT_OPTION = "option"

PLATFORM_SCHEMA_COMMON = vol.Schema(
    {
        vol.Required(CONF_HEATER): cv.entity_id,
        vol.Optional(CONF_SENSOR): cv.entity_id,
        vol.Optional(CONF_ADDITIONAL_MODES, default=False): cv.boolean,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(PLATFORM_SCHEMA_COMMON.schema)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize config entry."""
    await _async_setup_config(
        hass,
        PLATFORM_SCHEMA_COMMON(dict(config_entry.options)),
        None,
        async_add_entities,
    )

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the wire pilot climate platform."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    await _async_setup_config(
        hass, config, config.get(CONF_UNIQUE_ID), async_add_entities, None
    )

async def _async_setup_config(
    hass: HomeAssistant,
    config: ConfigType,
    unique_id: str | None,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the wire pilot climate platform."""
    name: str | None = config.get(CONF_NAME)
    wire_pilot_entity_id: str = config.get(CONF_HEATER)
    sensor_entity_id: str | None = config.get(CONF_SENSOR)
    additional_modes: bool = config.get(CONF_ADDITIONAL_MODES)

    async_add_entities(
        [
            NodonWirePilotClimate(
                hass,
                name,
                wire_pilot_entity_id,
                sensor_entity_id,
                additional_modes,
                unique_id,
            )
        ]
    )


class NodonWirePilotClimate(ClimateEntity):
    """Representation of a Nodon Wire Pilot device."""

    _attr_should_poll = False
    _attr_translation_key: str = "nodon_wire_pilot"
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        hass: HomeAssistant,
        name: str | None,
        wire_pilot_entity_id: str,
        sensor_entity_id: str | None,
        additional_modes: bool,
        unique_id: str | None,
    ) -> None:
        """Initialize the climate device."""

        registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        heater_entity = registry.async_get(wire_pilot_entity_id)
        device_id = heater_entity.device_id if heater_entity else None
        has_entity_name = heater_entity.has_entity_name if heater_entity else False

        self._device_id = device_id
        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )

        if name:
            self._attr_name = name

        self.wire_pilot_entity_id = wire_pilot_entity_id
        self.sensor_entity_id = sensor_entity_id
        self.additional_modes = additional_modes
        self._cur_temperature = None

        self._attr_has_entity_name = has_entity_name
        self._attr_unique_id = (
            unique_id or f"{DOMAIN}_{heater_entity_id}"
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        if self.sensor_entity_id is not None:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self.sensor_entity_id], self._async_sensor_changed
                )
            )

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self.wire_pilot_entity_id], self._async_heater_changed
            )
        )

        @callback
        def _async_startup(_: Event | None = None) -> None:
            """Init on startup."""
            if self.sensor_entity_id is not None:
                sensor_state = self.hass.states.get(self.sensor_entity_id)
                if sensor_state and sensor_state.state not in (
                    STATE_UNAVAILABLE,
                    STATE_UNKNOWN,
                ):
                    self._async_update_temp(sensor_state)
                    self.async_write_ha_state()

        if self.hass.state is CoreState.running:
            _async_startup()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )

    # Temperature
    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float | None:
        """Return the sensor temperature."""
        return self._cur_temperature

    @property
    def heater_value(self) -> str | None:
        """Return entity state."""
        state = self.hass.states.get(self.wire_pilot_entity_id)

        if state is None:
            return None

        return state.state

    # Presets
    @property
    def preset_modes(self) -> list[str] | None:
        """List of available preset modes."""
        if self.additional_modes:
            return [
                PRESET_COMFORT,
                PRESET_COMFORT_1,
                PRESET_COMFORT_2,
                PRESET_ECO,
                PRESET_AWAY,
                PRESET_NONE,
            ]
        else:
            return [
                PRESET_COMFORT,
                PRESET_ECO,
                PRESET_AWAY,
                PRESET_NONE,
            ]

    @property
    def preset_mode(self) -> str | None:
        """Preset current mode."""
        value = self.heater_value

        if value is None:
            return None
        if value == VALUE_OFF:
            return PRESET_NONE
        if value == VALUE_FROST:
            return PRESET_AWAY
        if value == VALUE_ECO:
            return PRESET_ECO
        if value == VALUE_COMFORT_2:
            return PRESET_COMFORT_2 if self.additional_modes else PRESET_COMFORT
        if value == VALUE_COMFORT_1:
            return PRESET_COMFORT_1 if self.additional_modes else PRESET_COMFORT
        if value == VALUE_COMFORT:
            return PRESET_COMFORT

        _LOGGER.warning(
            "Unexpected value '%s' for entity %s",
            value,
            self.wire_pilot_entity_id,
        )
        return None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode == PRESET_AWAY:
            value = VALUE_FROST
        elif preset_mode == PRESET_ECO:
            value = VALUE_ECO
        elif preset_mode == PRESET_COMFORT:
            value = VALUE_COMFORT
        elif preset_mode == PRESET_COMFORT_1 and self.additional_modes:
            value = VALUE_COMFORT_1
        elif preset_mode == PRESET_COMFORT_2 and self.additional_modes:
            value = VALUE_COMFORT_2
        elif preset_mode == PRESET_NONE:
            value = VALUE_OFF
        else:
            raise ValueError(f"Unsupported preset mode: {preset_mode}")

        await self._async_select_wire_pilot_mode(value)

    # Modes
    @property
    def hvac_modes(self) -> list[HVACMode]:
        """List of available operation modes."""
        return [
            HVACMode.HEAT,
            HVACMode.OFF
        ]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            value = VALUE_COMFORT
        elif hvac_mode == HVACMode.OFF:
            value = VALUE_OFF
        else:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")

        await self._async_select_wire_pilot_mode(value)

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, off mode."""
        value = self.heater_value

        if value is None:
            return None

        if value == VALUE_OFF:
            return HVACMode.OFF

        if value in (
            VALUE_FROST,
            VALUE_ECO,
            VALUE_COMFORT_2,
            VALUE_COMFORT_1,
            VALUE_COMFORT,
        ):
            return HVACMode.HEAT

        _LOGGER.warning(
            "Unexpected value '%s' for entity %s",
            value,
            self.wire_pilot_entity_id,
        )
        return None
    
    async def _async_sensor_changed(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle temperature changes."""
        new_state = event.data["new_state"]

        if new_state is None or new_state.state in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self._cur_temperature = None
            self.async_write_ha_state()
            return

        self._async_update_temp(new_state)
        self.async_write_ha_state()

    @callback
    def _async_heater_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle heater switch state changes."""
        new_state = event.data["new_state"]
        if new_state is None:
            return
        self.async_write_ha_state()

    @callback
    def _async_update_temp(self, state: State):
        try:
            cur_temp = float(state.state)
            if not math.isfinite(cur_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_temperature = cur_temp
        except ValueError as ex:
            self._cur_temperature = None
            _LOGGER.error("Unable to update from temperature sensor: %s", ex)

    async def _async_select_wire_pilot_mode(self, value: str) -> None:
        """Turn heater toggleable device on."""
        data = {
            ATTR_ENTITY_ID: self.wire_pilot_entity_id,
            SELECT_OPTION: value
        }

        await self.hass.services.async_call(SELECT_DOMAIN, SERVICE_SELECT_OPTION, data, blocking=True)
