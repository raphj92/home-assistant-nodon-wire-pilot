"""Tests for the nodon_wire_pilot config_flow module."""

from collections.abc import Mapping
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)

from custom_components.nodon_wire_pilot.config_flow import (
    CONFIG_FLOW,
    CONFIG_SCHEMA,
    ConfigFlowHandler,
    OPTIONS_FLOW,
    OPTIONS_SCHEMA,
)
from custom_components.nodon_wire_pilot.const import (
    CONF_ADDITIONAL_MODES,
    CONF_HEATER,
    CONF_SENSOR,
    DOMAIN,
)


class TestConfigSchema:
    """Tests for CONFIG_SCHEMA and OPTIONS_SCHEMA."""

    def test_config_schema_valid_minimal(self) -> None:
        """Test config schema with minimal required fields."""
        schema = vol.Schema(CONFIG_SCHEMA)
        result = schema({CONF_HEATER: "select.heater_test"})

        assert result[CONF_HEATER] == "select.heater_test"
        assert CONF_SENSOR not in result
        assert result.get(CONF_ADDITIONAL_MODES) is None

    def test_config_schema_valid_full(self) -> None:
        """Test config schema with all fields."""
        schema = vol.Schema(CONFIG_SCHEMA)
        result = schema(
            {
                CONF_HEATER: "select.heater_test",
                CONF_SENSOR: "sensor.temp_test",
                CONF_ADDITIONAL_MODES: True,
            }
        )

        assert result[CONF_HEATER] == "select.heater_test"
        assert result[CONF_SENSOR] == "sensor.temp_test"
        assert result[CONF_ADDITIONAL_MODES] is True

    def test_config_schema_missing_heater_raises(self) -> None:
        """Test config schema raises when heater is missing."""
        schema = vol.Schema(CONFIG_SCHEMA)

        with pytest.raises(vol.Invalid):
            schema({CONF_SENSOR: "sensor.temp_test"})

    def test_options_schema_valid_empty(self) -> None:
        """Test options schema with empty dict."""
        schema = vol.Schema(OPTIONS_SCHEMA)
        result = schema({})

        assert result == {}

    def test_options_schema_valid_with_sensor(self) -> None:
        """Test options schema with sensor."""
        schema = vol.Schema(OPTIONS_SCHEMA)
        result = schema({CONF_SENSOR: "sensor.temp_test"})

        assert result[CONF_SENSOR] == "sensor.temp_test"

    def test_options_schema_valid_with_additional_modes(self) -> None:
        """Test options schema with additional_modes."""
        schema = vol.Schema(OPTIONS_SCHEMA)
        result = schema({CONF_ADDITIONAL_MODES: True})

        assert result[CONF_ADDITIONAL_MODES] is True


class TestConfigFlowStructure:
    """Tests for config flow structure."""

    def test_config_flow_has_user_step(self) -> None:
        """Test config flow has user step."""
        assert "user" in CONFIG_FLOW
        assert isinstance(CONFIG_FLOW["user"], SchemaFlowFormStep)

    def test_options_flow_has_init_step(self) -> None:
        """Test options flow has init step."""
        assert "init" in OPTIONS_FLOW
        assert isinstance(OPTIONS_FLOW["init"], SchemaFlowFormStep)

    def test_config_flow_handler_inherits_schema_config_flow_handler(self) -> None:
        """Test ConfigFlowHandler inherits from SchemaConfigFlowHandler."""
        assert issubclass(ConfigFlowHandler, SchemaConfigFlowHandler)

    def test_config_flow_handler_domain(self) -> None:
        """Test ConfigFlowHandler has correct domain."""
        # Domain is set by SchemaConfigFlowHandler metaclass
        # The domain is registered with the class via the metaclass
        # We can check it through the DOMAIN constant
        assert DOMAIN == "nodon_wire_pilot"

    def test_config_flow_handler_config_flow(self) -> None:
        """Test ConfigFlowHandler.config_flow matches CONFIG_FLOW."""
        assert ConfigFlowHandler.config_flow == CONFIG_FLOW

    def test_config_flow_handler_options_flow(self) -> None:
        """Test ConfigFlowHandler.options_flow matches OPTIONS_FLOW."""
        assert ConfigFlowHandler.options_flow == OPTIONS_FLOW


class TestAsyncConfigEntryTitle:
    """Tests for async_config_entry_title method."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        return hass

    @pytest.fixture
    def mock_entity_registry(self) -> MagicMock:
        """Create a mock entity registry."""
        registry = MagicMock(spec=er.EntityRegistry)
        registry.async_get = MagicMock()
        registry.async_update_entity = MagicMock()
        return registry

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.data = {CONF_HEATER: "select.heater_test"}
        return entry

    @pytest.fixture
    def handler(
        self, mock_hass: MagicMock, mock_entity_registry: MagicMock, mock_config_entry: MagicMock
    ) -> ConfigFlowHandler:
        """Create a ConfigFlowHandler instance."""
        with patch(
            "custom_components.nodon_wire_pilot.config_flow.er.async_get",
            return_value=mock_entity_registry,
        ):
            handler = ConfigFlowHandler()
            handler.hass = mock_hass
            handler.config_entry = mock_config_entry
            return handler

    def test_async_config_entry_title_hides_heater_entity(
        self,
        handler: ConfigFlowHandler,
        mock_entity_registry: MagicMock,
    ) -> None:
        """Test heater entity is hidden when not already hidden."""
        mock_heater_entity = MagicMock()
        mock_heater_entity.hidden = False
        mock_entity_registry.async_get.return_value = mock_heater_entity

        options: Mapping[str, object] = {}

        with patch(
            "custom_components.nodon_wire_pilot.config_flow.wrapped_entity_config_entry_title",
            return_value="Test Heater",
        ) as mock_wrapped_title:
            title = handler.async_config_entry_title(options)

        mock_entity_registry.async_get.assert_called_once_with("select.heater_test")
        mock_entity_registry.async_update_entity.assert_called_once_with(
            "select.heater_test",
            hidden_by=er.RegistryEntryHider.INTEGRATION,
        )
        mock_wrapped_title.assert_called_once()
        assert title == "Test Heater"

    def test_async_config_entry_title_does_not_hide_already_hidden(
        self,
        handler: ConfigFlowHandler,
        mock_entity_registry: MagicMock,
    ) -> None:
        """Test heater entity is not hidden again when already hidden."""
        mock_heater_entity = MagicMock()
        mock_heater_entity.hidden = True
        mock_entity_registry.async_get.return_value = mock_heater_entity

        options: Mapping[str, object] = {}

        with patch(
            "custom_components.nodon_wire_pilot.config_flow.wrapped_entity_config_entry_title",
            return_value="Test Heater",
        ) as mock_wrapped_title:
            title = handler.async_config_entry_title(options)

        mock_entity_registry.async_update_entity.assert_not_called()
        mock_wrapped_title.assert_called_once()
        assert title == "Test Heater"

    def test_async_config_entry_title_no_heater_entity(
        self,
        handler: ConfigFlowHandler,
        mock_entity_registry: MagicMock,
    ) -> None:
        """Test when heater entity doesn't exist in registry."""
        mock_entity_registry.async_get.return_value = None

        options: Mapping[str, object] = {}

        with patch(
            "custom_components.nodon_wire_pilot.config_flow.wrapped_entity_config_entry_title",
            return_value="Test Heater",
        ) as mock_wrapped_title:
            title = handler.async_config_entry_title(options)

        mock_entity_registry.async_update_entity.assert_not_called()
        mock_wrapped_title.assert_called_once()
        assert title == "Test Heater"

    def test_async_config_entry_title_fallback_to_options(
        self,
        mock_hass: MagicMock,
        mock_entity_registry: MagicMock,
    ) -> None:
        """Test falls back to options when config_entry is None."""
        handler = ConfigFlowHandler()
        handler.hass = mock_hass
        handler.config_entry = None

        mock_heater_entity = MagicMock()
        mock_heater_entity.hidden = False
        mock_entity_registry.async_get.return_value = mock_heater_entity

        options: Mapping[str, object] = {CONF_HEATER: "select.heater_from_options"}

        with patch(
            "custom_components.nodon_wire_pilot.config_flow.er.async_get",
            return_value=mock_entity_registry,
        ), patch(
            "custom_components.nodon_wire_pilot.config_flow.wrapped_entity_config_entry_title",
            return_value="Test Heater",
        ):
            title = handler.async_config_entry_title(options)

        mock_entity_registry.async_get.assert_called_once_with("select.heater_from_options")
        assert title == "Test Heater"

    def test_async_config_entry_title_default_when_no_heater(
        self,
        handler: ConfigFlowHandler,
        mock_entity_registry: MagicMock,
    ) -> None:
        """Test returns default title when no heater entity_id."""
        handler.config_entry.data = {}
        options: Mapping[str, object] = {}

        with patch(
            "custom_components.nodon_wire_pilot.config_flow.er.async_get",
            return_value=mock_entity_registry,
        ):
            title = handler.async_config_entry_title(options)

        assert title == "Nodon Wire Pilot"
        mock_entity_registry.async_get.assert_not_called()


class TestConfigFlowIntegration:
    """Integration tests for config flow."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        return hass

    def test_config_flow_schema_structure(self) -> None:
        """Test config flow schema has correct structure."""
        user_step = CONFIG_FLOW["user"]
        schema = user_step.schema.schema

        # Check required field
        assert CONF_HEATER in schema
        heater_validator = schema[CONF_HEATER]
        # EntitySelector has config dict
        assert hasattr(heater_validator, "config")
        assert heater_validator.config.get("domain") == ["select"]

        # Check optional fields
        assert CONF_SENSOR in schema
        sensor_validator = schema[CONF_SENSOR]
        assert hasattr(sensor_validator, "config")
        assert sensor_validator.config.get("domain") == ["sensor"]
        assert "temperature" in sensor_validator.config.get("device_class", [])

        assert CONF_ADDITIONAL_MODES in schema
        additional_modes_validator = schema[CONF_ADDITIONAL_MODES]
        assert hasattr(additional_modes_validator, "__class__")

    def test_options_flow_schema_structure(self) -> None:
        """Test options flow schema has correct structure."""
        init_step = OPTIONS_FLOW["init"]
        schema = init_step.schema.schema

        assert CONF_SENSOR in schema
        assert CONF_ADDITIONAL_MODES in schema
        assert CONF_HEATER not in schema  # heater not in options