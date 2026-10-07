# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a fork of [MLB-LED-Scoreboard](https://github.com/MLB-LED-Scoreboard/mlb-led-scoreboard) (`upstream` remote), rebased onto upstream v9. See "Fork customizations" below for what is ours.

## Commands

**Run (hardware):** `sudo ./main.py`

**Run (emulator, no hardware needed):** `./main.py --emulated`

**Run with custom config:** `./main.py --config=custom_config` (omit `.json`). Board dimensions come from CLI args (`--led-rows`, `--led-cols`).

**Run tests:** `RGBME_SUPPRESS_ADAPTER_LOAD_ERRORS=1 python -m unittest`

**Format:** `black -l 120 .` (upstream code is black-clean)

**Regenerate example files:** `python -m schemas --overwrite`. Check without writing: `python -m schemas --check`

**Validate/upgrade a config:** `python validate_config.py`. A v8 config is migrated with `upgrade_to_v9.py`, which drops custom keys, so merge them by hand.

**Install:** `pip install -r requirements.txt -r requirements.dev.txt` (inside a venv). The local packages `./bullpen`, `./standings`, `./news` and `./boards` are installed from `requirements.txt`. Plugins are discovered through entry points, so a new or changed plugin package needs a reinstall. On a Pi use `sudo ./install.sh`.

## Architecture

Two threads, as in upstream:

- **Main thread** (`main.py`): loops `data.refresh_schedule()`, `data.refresh_game()` and `data.refresh_plugin(name)`.
- **Render thread** (`MainRenderer` in `renderers/main.py`): endless loop. Draws the games at the current priority, then runs each plugin screen configured for that priority.

Screen routing is **priority based**, not `ScreenType` based. `rotation.screens` in `config.json` is a list of rules. `game` and `secondary_game` rules (optionally filtered by `teams` and `required_status`) pick which games show, and the highest matching priority wins. `time` rules add a priority at certain times of day. Any other `kind` is a plugin screen (`news`, `standings`, `clock`, `countdown`, ...) with `seconds` and `with_priority`. At least one screen must be at priority 0, which is what shows when there are no games.

### Plugins (`bullpen/`)

Plugins register through the entry point group `bullpen.mlbled.plugin`, and only plugins named in a rotation rule are loaded (`data/plugins.py`). Each plugin provides `(Config, Data, Renderer)`, subclassing `bullpen.api.PluginConfig`, `PluginData` and `PluginRenderer`.

- Settings come from `plugins.<name>` in `config.json`; layout and colors from `plugins.<name>` in the coordinates and colors files. `news` and `standings` are the legacy exceptions that use top-level keys.
- The host draws the network-error icon and swaps the canvas. A plugin must fill its own background.
- In-repo plugins: `news/`, `standings/` (upstream) and `boards/` (ours).

### Configuration is schema-first

`schemas/*.schema.json` define every config, coordinates and colors file, and `config.example.json`, `coordinates/*.example.json` and `colors/*.example.json` are **generated** from the schema defaults. Never hand-edit an example. Change the schema default and run `python -m schemas --overwrite`.

Custom `colors/scoreboard.json`, `colors/teams.json`, `coordinates/wXhY.json` and `config.json` are gitignored and are merged on top of the examples. Tests use `tests/fixtures/` instead, where color values are the marker `1,2,3` and coordinates are `99`, so a new color block needs a matching entry in `tests/fixtures/colors/scoreboard.json`.

### Key modules

- `data/schedule.py`: fetches every league, filters games by priority, keeps a sync-delay queue.
- `data/game.py`: game model. `data/scoreboard/`: per-screen models built from a game.
- `renderers/games/`: live (`game.py`), pregame, postgame, `teams.py` (banner), `linescore.py`.
- `data/config/`: `Config`, `Layout` and `Color`, plus the rule parsers.
- `cli.py`: argument parsing. `driver/`: wraps `rgbmatrix` and falls back to `RGBMatrixEmulator`.

## Fork customizations

Keep these when merging upstream:

- **Linescore** (`data/scoreboard/linescore.py`, `renderers/games/linescore.py`): inning-by-inning runs on the postgame screen, enabled per size in `coordinates` (`linescore.enabled`). Colors under `linescore.*`.
- **Short team names** (`TEAM_ID_SHORT_NAME` in `data/teams.py`, `team_display_name` in `renderers/games/teams.py`): with `teams.line_score.shorten_team_name_on_high_line_score`, long names switch to a short alternate at double-digit runs/hits (7-character names need both). Also lifts a near-black home banner to dark grey.
- **`show_yesterday_scores`** (`data/schedule.py`): shows yesterday's finals until `hours_before_first_game` before today's first pitch. A day with no games is never replaced.
- **Extra innings**: the postgame scroll starts with `Final/N` when the game didn't end in the 9th.
- **HomeKit / brightness / spoiler mode** (`homekit_server.py`, `brightness_manager.py`, `spoiler_mode_manager.py`): a HomeKit bridge with a brightness light, a global "Spoiler Mode" switch and one switch per preferred team. `Config.preferred_teams` is derived from the `teams` named in game rules. `MainRenderer.__swap` keeps the board black while powered off, and `__is_spoiler_free` hides live and postgame content and the score. State lives in `.brightness_state`, `.spoiler_mode_state` and `accessory.state` (gitignored; `accessory.state` is the HomeKit pairing, so don't delete it). The setup code comes from `HOMEKIT_PINCODE` or is generated and printed at startup.
- **Clock and countdown plugins** (`boards/`): add `{"kind": "clock"|"countdown", "seconds": N, "with_priority": P}` to `rotation.screens`. Countdown takes `plugins.countdown.events` (`label` with optional `[red]...[/]` or `[#rrggbb]` color tags, and `date` as `MM-DD`, `MM-DD-YY` or `YYYY-MM-DD`) and `item_duration`. Set the rule's `seconds` to about events x `item_duration`.
- **`rotation.rates.live_preferred`** (`Config.rotate_rate_for_game`): seconds per live game that includes a team named in a game rule (v8 used 60s for preferred teams). Falls back to `rates.live` when omitted.
- **`--led-slowdown-gpio`** accepts 0-5 (`cli.py`).

The v8 fork's `boards` contexts (`offday`, `no_preferred_playing`, `inning_break`) are gone: use priorities instead. `fork-v8-final` is the tag of the last v8 commit.

## Deployment (the Pi)

The scoreboard runs on a Raspberry Pi Zero 2 W (about 415 MB usable RAM), reachable as `ssh score`, from `~/mlb-v9` (a clone of this repo's `master`) with its own `venv`. The systemd unit is `/etc/systemd/system/mlb-scoreboard.service`, running as root with `--config=config-v9 --led-rows=32 --led-cols=64 --led-chain=1 --led-slowdown-gpio=5 --led-gpio-mapping=adafruit-hat-pwm --led-pwm-bits=9 --led-limit-refresh=100`. The old v8 checkout is still at `~/mlb-led-scoreboard`, and the v8 unit is saved as `mlb-scoreboard.service.v8.bak`. `chip` can start, stop and restart the service without a password; anything else needs sudo.

- **Don't compile `rgbmatrix` on this Pi.** `requirements.rpi.txt` builds the C++ bindings from a pinned git commit, and that build rebooted the Zero 2 W (most likely out of memory; a power sag is also possible, and no journal survived to confirm). The venv instead uses the library already built for v8: copy `rgbmatrix/` and `rgbmatrix-0.0.1-py3.13.egg-info/` from `~/mlb-led-scoreboard/venv/lib/python3.13/site-packages/` into the new venv's `site-packages/`. Installing `requirements.txt` (without `requirements.rpi.txt`) and then copying those two directories is the working recipe.
- **What the old build lacks:** only `rp1_pio` (Raspberry Pi 5 support), which logs a harmless "compiled RGB Matrix Library is out of date" warning. Every other option v9 passes is supported, including `--led-limit-refresh` and `--led-pwm-dither-bits`.
- **Flicker/colors:** `--led-pwm-bits=7` washes out dim colors, 9 or 11 bits fix that but flicker, and 9 bits with `--led-limit-refresh=100` gave steady colors with no flicker.
- **`--emulated` does not work on the Pi:** `rgbmatrix` is importable there, so `driver/` always picks the hardware driver and `--emulated` produces a mixed hardware/emulator canvas.
- **Only one HomeKit bridge may run at a time.** v8 and v9 share the same `accessory.state` identity, so stop the service before running `main.py` by hand, and copy the live `accessory.state`, `.brightness_state` and `.spoiler_mode_state` between checkouts when switching.
- **Testing a past day:** `demo_date` in a config replays a date from the API, e.g. `"2026-09-27"` for games where the Cubs and Angels both played.

## Tests

Tests live in `tests/`, plus `standings/tests/`. They run in emulator mode and need no hardware. Use `tests/helpers.py::make_test_config` to build a `Config` against `tests/fixtures/`. `tests/test_schedule.py` and `tests/test_data_up_to_date.py` call the live MLB API, so they need network access.
