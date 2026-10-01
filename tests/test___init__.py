"""Tests for the nodon_wire_pilot __init__ module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.nodon_wire_pilot import (
    async_setup_entry,
    async_unload_entry,
    config_entry_update_listener,
)
from custom_components.nodon_wire_pilot.const import CONF_HEATER, DOMAIN, PLATFORMS


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_HEATER: "select.heater_living_room"}
    entry.options = {}
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    return entry


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test successful setup entry."""
        with patch(
            "custom_components.nodon_wire_pilot.async_remove_stale_devices_links_keep_entity_device"
        ) as mock_remove_stale:
            result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_remove_stale.assert_called_once_with(
            mock_hass, mock_config_entry.entry_id, mock_config_entry.data[CONF_HEATER]
        )
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            mock_config_entry, PLATFORMS
        )
        mock_config_entry.add_update_listener.assert_called_once_with(
            config_entry_update_listener
        )

    @pytest.mark.asyncio
    async def test_async_setup_entry_forward_setups_fails(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test setup entry when forward_entry_setups fails."""
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock(
            side_effect=Exception("Setup failed")
        )

        with patch(
            "custom_components.nodon_wire_pilot.async_remove_stale_devices_links_keep_entity_device"
        ):
            with pytest.raises(Exception, match="Setup failed"):
                await async_setup_entry(mock_hass, mock_config_entry)


class TestConfigEntryUpdateListener:
    """Tests for config_entry_update_listener function."""

    @pytest.mark.asyncio
    async def test_config_entry_update_listener(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test config entry update listener calls reload."""
        await config_entry_update_listener(mock_hass, mock_config_entry)

        mock_hass.config_entries.async_reload.assert_called_once_with(
            mock_config_entry.entry_id
        )


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry function."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test successful unload entry."""
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_hass.config_entries.async_unload_platforms.assert_called_once_with(
            mock_config_entry, PLATFORMS
        )

    @pytest.mark.asyncio
    async def test_async_unload_entry_failure(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test unload entry when unload_platforms fails."""
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is False
        mock_hass.config_entries.async_unload_platforms.assert_called_once_with(
            mock_config_entry, PLATFORMS
        )