"""Test init and entry lifecycle for Plate Recognizer."""
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.platerecognizer.const import DOMAIN


async def test_setup_and_unload_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test setting up and unloading Plate Recognizer."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED

    # Verify entities registered
    remaining_sensors = [s for s in hass.states.async_entity_ids("sensor") if "remaining_calls" in s]
    assert len(remaining_sensors) == 1
    remaining_sensor = hass.states.get(remaining_sensors[0])
    assert remaining_sensor.state == "2380"  # 2500 - 120

    last_plate_sensors = [s for s in hass.states.async_entity_ids("sensor") if "last_plate" in s]
    assert len(last_plate_sensors) == 1

    scan_buttons = [s for s in hass.states.async_entity_ids("button") if "scan" in s]
    assert len(scan_buttons) == 1

    image_entities = [s for s in hass.states.async_entity_ids("image") if "last_frame" in s]
    assert len(image_entities) == 1

    # Test unload
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
