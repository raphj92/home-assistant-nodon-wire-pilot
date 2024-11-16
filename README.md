# home-assistant-nodon-wire-pilot

Home Assistant Component for Nodon Wire Pilot (forked from [@NicolasHng's](https://github.com/nicolashng) [home-assistant-nodon-wire-pilot](https://github.com/nicolashng/home-assistant-nodon-wire-pilot)) 

## Introduction

The Nodon SIN-4-FP-21 is not recognized as a thermostat in Home Assistant but as a select entities.
The select options is mapped to a mode.

| Mode             | Option           |
| :--------------- | :--------------- |
| Off              | off              |
| Frost protection | frost_protection |
| Eco              | eco              |
| Comfort -2       | comfort_-2       |
| Comfort -1       | comfort_-1       |
| Comfort          | comfort          |

This component create a `climate` entity using the `select` entity.

The climate will have 2 modes :

- `heat` - splitted into 3 or 5 presets :
  - `comfort` - mapped nodon "Comfort" mode
  - `comfort-1` - mapped nodon "Comfort -1" mode (optional)
  - `comfort-2` - mapped nodon "Comfort -2" mode (optional)
  - `eco` - mapped nodon "Eco" mode
  - `away` - mapped nodon "Frost protection" mode
- `off` - mapped nodon "Off" mode :

:warning: "Comfort -1" and "Comfort -2" are not available by default because home assistant doesn't have comfort-1 and comfort-2 preset. If you want to support these modes, add `additional_modes: true` in your configuration.

## Configuration

| Key                | Type    | Required | Description                                                                                                               |
| :----------------- | :------ | :------- | :------------------------------------------------------------------------------------------------------------------------ |
| `platform`         | string  | yes      | Platform name                                                                                                             |
| `heater`           | string  | yes      | Select entity                                                                                                              |
| `sensor`           | string  | no       | Temperature sensor (for display)                                                                                          |
| `additional_modes` | boolean | no       | 6-order support (add Comfort -1 and Comfort -2 preset)                                                                    |
| `name`             | string  | no       | Name to use in the frontend.                                                                                              |
| `unique_id`        | string  | no       | An ID that uniquely identifies this climate. If two climates have the same unique ID, Home Assistant will raise an error. |

The unique id is recommended to allow icon, entity_id or name changes from the UI.

## Example

```yaml
climate:
  - platform: nodon_wire_pilot
    heater: select.heater_living_room_dimmer
```

with 6 order

```yaml
climate:
  - platform: nodon_wire_pilot
    heater: select.heater_living_room_dimmer
    additional_modes: true
```

with optional sensor

```yaml
climate:
  - platform: nodon_wire_pilot
    heater: select.heater_living_room_dimmer
    sensor: sensor.temperature_living_room
```

## Unique ID

The `unique_id` is used to edit the entity from the GUI. It's automatically generated from heater entity_id. As the `unique_id` must be unique, you can not create 2 entities with the same heater.

If you want to have 2 climate with the same heater, you must specify the `unique_id` in the config.

```yaml
climate:
  - platform: nodon_wire_pilot
    heater: select.heater_living_room_dimmer
    unique_id: nodon_heater_living_room_1
  - platform: nodon_wire_pilot
    heater: select.heater_living_room_dimmer
    unique_id: nodon_heater_living_room_2
```

## Lovelace

You can use the [climate-mode-entity-row](https://github.com/piitaya/lovelace-climate-mode-entity-row) card in your lovelace dashboard to easily switch between modes.
