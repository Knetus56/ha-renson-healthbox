<p align="center"><img src="icon.png" width="96" alt="Renson logo"></p>

# Renson Healthbox - Home Assistant Integration

[![Validate](https://github.com/Knetus56/ha-renson-healthbox/actions/workflows/validate.yml/badge.svg)](https://github.com/Knetus56/ha-renson-healthbox/actions/workflows/validate.yml)

A [Home Assistant](https://www.home-assistant.io/) integration to monitor and control your **Renson Healthbox 3** locally over its HTTP API, without going through the Renson cloud.

Complete rewrite of [rmassch/healthbox-hacs](https://github.com/rmassch/healthbox-hacs) (see [Credits](#-credits)), fixing several bugs in the original and modernizing the code to current Home Assistant standards.

## 🌟 Features

- 📊 **Real-time monitoring**: air quality, temperature, humidity, CO2, VOC, ventilation rate, per room
- 🌀 **Boost control**: a `switch` per room to start/stop the boost, with adjustable level and duration
- 🎛️ **Profile switching**: `select` per room (Eco / Health / Intense), changeable directly from the dashboard
- 🏠 **Multi-room**: each Healthbox room becomes its own HA device, linked to the hub
- 🔍 **Automatic sensor discovery**: CO2, VOC, etc. only show up if the module is actually installed in that room - and are added on the fly if they appear later
- 🔐 **Local connection**: no data ever goes through a cloud
- 🔑 **API key required**: needed from setup to unlock per-room sensors (temperature, humidity, CO2, VOC, air quality, boost, profile) - without it the integration provides almost nothing useful
- ⚙️ **Editable afterwards**: change the API key or the poll interval without recreating the integration
- 🩺 **Built-in diagnostics** and detailed **debug logs** to make bug reports easier
- 🇫🇷 **Localized UI**: French and English (the config screen follows Home Assistant's language)

## 📋 Sensors

### Hub sensors (Healthbox)

| Sensor | Description | Unit |
|---|---|---|
| `global_air_quality_index` | Global air quality index | - |
| `error_count` | Number of errors reported by the device | - |
| `fan_voltage` | Fan voltage | V |
| `fan_pressure` | Fan pressure | Pa |
| `fan_flow` | Fan flow | m³/h |
| `fan_power` | Fan power | W |
| `fan_rpm` | Fan speed | RPM |
| `wifi_status` *(diagnostic)* | Wi-Fi connection status | - |
| `wifi_internet_connection` *(diagnostic)* | Internet access via Wi-Fi | - |
| `wifi_ssid` *(diagnostic)* | Wi-Fi network name | - |

### Per-room sensors (require the API key)

| Sensor | Description | Unit |
|---|---|---|
| `temperature` | Indoor temperature | °C |
| `humidity` | Relative humidity | % |
| `co2_concentration` | CO2 concentration *(if the module is installed)* | ppm |
| `volatile_organic_compounds` | Volatile organic compounds *(if the module is installed)* | ppm |
| `air_quality_index` | Room air quality | - |
| `airflow_ventilation_rate` | Ventilation rate | % |
| `boost_level` | Current boost level | % |
| `boost_remaining` | Time left on the current boost | s |

## 🔌 Control entities

| Entity | Domain | Description |
|---|---|---|
| `select.healthbox_<room>_profile` | `select` | Ventilation profile: Eco / Health / Intense |
| `switch.healthbox_<room>_boost` | `switch` | Starts/stops the boost; reflects the device's actual state (flips back to `off` on its own once the delay ends) |
| `number.healthbox_<room>_boost_level` | `number` | Level (%) to use the next time the boost starts |
| `number.healthbox_<room>_boost_timeout` | `number` | Duration (minutes) to use the next time the boost starts |

## 🔄 Services

- `healthbox.start_room_boost` - start a room's boost (level %, duration in minutes)
- `healthbox.stop_room_boost` - stop a room's boost
- `healthbox.change_room_profile` - change a room's profile (Eco/Health/Intense)

All three target a **Healthbox Room** device. They do exactly the same thing as the switch/select above - useful for automations that prefer calling a service over manipulating an entity.

```yaml
service: healthbox.start_room_boost
target:
  device_id: <room's device_id>
data:
  boost_level: 150
  boost_timeout: 30
```

## 🚀 Installation

### Requirements

- Home Assistant 2024.8+
- Network access to the Healthbox
- The Healthbox's IP address and its **API key** (required - found in the device's own web UI)

### Via HACS (custom repository)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Knetus56&repository=ha-renson-healthbox&category=integration)

Or manually:
1. **HACS** > **Integrations** > **⋮** menu > **Custom repositories**
2. Add the URL `https://github.com/Knetus56/ha-renson-healthbox`, category **Integration**
3. Search for and install **Renson Healthbox**
4. Restart Home Assistant

*(Submitted to the official HACS store - [PR pending review](https://github.com/hacs/default/pull/10693).)*

### Manual installation

1. Copy `custom_components/healthbox` into your Home Assistant configuration's `custom_components` folder
2. Restart Home Assistant

## ⚙️ Configuration

### Initial setup

1. **Settings** > **Devices & services** > **Add integration**
2. Search for **Renson Healthbox**
3. Fill in:
   - **IP address**: required
   - **API key**: **required** - without it the integration only exposes a handful of global sensors; it unlocks the per-room sensors (temperature, humidity, CO2, VOC, air quality, boost, profile)

### Changing the configuration after installation

1. **Settings** > **Devices & services** > **Renson Healthbox** card > **Configure**
2. Update the **API key** and/or the **poll interval**
3. Submit - the integration reloads automatically

## 🔧 Advanced configuration

### Poll interval

By default, the integration polls the Healthbox every **30 seconds**. Adjustable from 10 to 3600 seconds from the **Configure** screen.

### Sensors that don't show up

Per-room sensors depend on which modules are physically installed (e.g. one room may have a CO2 sensor, another a VOC sensor, a third neither) and on the API key being set. A sensor that becomes available later (API key added, module detected) is added automatically on the next poll cycle, with no restart or reconfiguration needed.

## 🐛 Reporting a bug

Please include both of these with any issue:

1. **Debug logs**: **Settings** > **Devices & services** > **Renson Healthbox** > the device's **⋯** menu > **Enable debug logging**. Reproduce the problem, then **Disable debug logging** from the same menu to download the log file. YAML equivalent:
   ```yaml
   logger:
     logs:
       custom_components.healthbox: debug
       pyhealthbox3: debug
   ```
2. **Diagnostics**: **Settings** > **Devices & services** > **Renson Healthbox** > **⋯** > **Download diagnostics** (the API key is automatically redacted).

Then open an issue at [Knetus56/ha-renson-healthbox/issues](https://github.com/Knetus56/ha-renson-healthbox/issues).

## 📦 Versions

- **1.1.1** (2026-09-06) - Internal cleanup: dynamic entity discovery factored into a single shared helper (instead of 4 copies), correct rounding (`round()` instead of a silent truncation) on the boost level/duration, O(1) room lookup, test coverage added for control-entity availability.
- **1.1.0** (2026-09-06) - `select` for the room profile, `switch` + `number` to drive the boost (adjustable level/duration, persisted across restarts), detailed debug logs, sensors rounded to whole numbers (temperature kept at 1 decimal), French translation.

## 🙏 Credits

- [rmassch](https://github.com/rmassch/healthbox-hacs) for the original integration
- The author of [pyhealthbox3](https://pypi.org/project/pyhealthbox3/), the client library this integration uses as-is
