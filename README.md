<p align="center"><img src="icon.png" width="96" alt="Renson logo"></p>

# Renson Healthbox (`ha-renson-healthbox`)

Home Assistant custom integration for the Renson Healthbox 3 ventilation
unit, talking to its local API via [pyhealthbox3](https://pypi.org/project/pyhealthbox3/).

This is a from-scratch rewrite of
[rmassch/healthbox-hacs](https://github.com/rmassch/healthbox-hacs), whose
`__init__.py`/`config_flow.py`/`const.py`/`sensor.py`/`binary_sensor.py` were
audited and found to have several real bugs and drifted from current Home
Assistant conventions. Thanks to the original author for the integration and
to pyhealthbox3's maintainer for the API client — this repo keeps using that
library as-is, only the Home Assistant integration layer was rewritten.

## What changed vs. the original

- **Options flow actually validates the API key.** The original wrote the
  new key to the config entry *before* validating it, swallowed the auth
  exception, and always returned success — an invalid key was silently
  accepted. This rewrite validates first and only saves on success, showing
  a real error otherwise.
- **One place stores each setting.** `entry.data` holds connection identity
  (host, API key); `entry.options` holds behaviour tuning (poll interval).
  The original wrote to both inconsistently, with `entry.options` never
  actually read back anywhere.
- **No more aiohttp session leaks.** Every client uses Home Assistant's
  shared session (`async_get_clientsession`) instead of creating a
  throwaway one per config-flow attempt.
- **Services survive multi-device unload.** `start_room_boost`,
  `stop_room_boost` and `change_room_profile` are registered once for the
  integration and resolve their target device to whichever config entry
  actually owns it — removing one Healthbox no longer deletes the services
  for every other Healthbox you have configured.
- **Sensors don't crash on a value that goes missing.** e.g. airflow
  ventilation rate briefly disappearing used to throw
  (`None * 100`) inside the sensor's `native_value`; reads are now
  defensive, and a room device that disappears is marked unavailable
  instead of raising on every poll.
- **New sensors can appear without a reload.** Optional per-room sensors
  (CO2, VOC, temperature/humidity — only present if that room actually has
  the matching module) and hub diagnostics (Wi-Fi SSID, fan metrics) are
  (re-)discovered on every poll, not only at startup.
- **Namespaced entity IDs.** The original named per-room entities directly
  after the room (`sensor.cuisine_temperature`), which can collide with any
  other integration's "Cuisine" entity. Devices are now named
  `Healthbox <room>` / `Healthbox <serial>`, so IDs come out as
  `sensor.healthbox_cuisine_temperature` — **this is a breaking rename**,
  see below.
- **Rooms are linked to their hub** in the device registry (`via_device`),
  so they show up nested under the Healthbox device instead of floating on
  their own.
- **Up to date unit constants.** Uses `UnitOfRatio.PARTS_PER_MILLION`
  instead of the deprecated `CONCENTRATION_PARTS_PER_MILLION` (removed in
  HA Core 2027.8).
- **`diagnostics.py`** added (Settings → Devices & Services → Renson
  Healthbox → ⋯ → Download diagnostics), with the API key redacted.
- **Bundled brand icon** (`custom_components/healthbox/brand/`) — the
  domain had never been submitted anywhere, so it showed a generic
  puzzle-piece icon. Since HA 2026.3 a custom integration can ship its own
  `icon.png`/`icon@2x.png` and HA serves it directly (no PR to
  `home-assistant/brands` needed, unlike before that version).
- Dead data-model code removed from `const.py` (a hand-rolled JSON model
  that duplicated, and had drifted from, what `pyhealthbox3` already
  provides).
- `strings.json` and `translations/en.json` are kept byte-identical, with
  CI (`.github/workflows/validate.yml`) failing the build if they ever
  drift apart again.

## Breaking change: entity IDs

Because per-room entity IDs are now namespaced under the device name, they
will change on first install, e.g.:

| Before                        | After                                    |
|--------------------------------|-------------------------------------------|
| `sensor.cuisine_temperature`   | `sensor.healthbox_cuisine_temperature`    |
| `binary_sensor.sdb_boost_status` | `binary_sensor.healthbox_sdb_boost_status` |

Update any automations, scripts, or dashboards that reference the old
entity IDs after migrating.

## Installation

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/Knetus56/ha-renson-healthbox`, category **Integration**.
3. Install "Renson Healthbox", restart Home Assistant.

### Manual

Copy `custom_components/healthbox` into your Home Assistant's
`custom_components` directory and restart.

## Configuration

Settings → Devices & Services → Add Integration → **Renson Healthbox**.

- **IP address**: required.
- **API key**: optional. Without it you get device-level sensors (fan
  metrics, Wi-Fi, global air quality, error count). With it (found in the
  Healthbox's own web UI), per-room sensors (temperature, humidity, CO2,
  VOC, air quality, boost, profile) are unlocked.

The poll interval and the API key can be changed later from the
integration's **Configure** button.

## Services

- `healthbox.start_room_boost` — boost a room's fan (level %, duration).
- `healthbox.stop_room_boost` — stop boosting a room's fan.
- `healthbox.change_room_profile` — set a room's profile (Eco/Health/Intense).

All three target a **Healthbox Room** device.

## Known limitations

- `pyhealthbox3` itself swallows most exceptions from its secondary
  endpoints (errors, Wi-Fi, fan, per-room boost) and simply leaves the
  corresponding field `None` on failure — this integration reads defensively
  around that, but a transient error on those endpoints is invisible in the
  logs by design of the library, not this integration.
- `tests/` covers the two concrete bugs this rewrite fixes (options flow
  validation order, services surviving a multi-entry unload) plus a
  setup smoke test, using `pytest-homeassistant-custom-component`. Run with
  `pip install -r requirements-test.txt && pytest`. Coverage is deliberately
  narrow (the bug fixes, not every code path) — also validated against a
  live Healthbox 3 through Home Assistant's MCP tools during development.

## License

MIT — see [LICENSE](LICENSE).
