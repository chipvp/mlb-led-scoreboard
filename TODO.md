# TODO

## Bigger features

- [x] **Per-team spoiler switches** — one switch per preferred team plus a global "Spoiler Mode" switch. The switches and the HomeKit bridge now live in the separate `led-panel-control` project (`~/projects/led-panel-control`); `spoiler_mode_manager.py` only reads `/var/lib/led-panel/spoiler`.
- [x] **Linescore display** — inning-by-inning run totals on the final screen. Still open: show it for live games too.
- [x] **HomeKit brightness state isn't kept across reboots / service restarts** — fixed in `led-panel-control` (`~/projects/led-panel-control`), which owns `/var/lib/led-panel/state`; `brightness_manager.py` only reads it.
- [ ] **Auto-brightness by time of day** — dim display at night automatically without needing HomeKit.
- [ ] **Pitch speed/type on live games** — coordinates/color config already support `atbat.pitch`; verify it's wired up and enabled by default.

## Scoreboard content ideas

Tier 1 (data already fetched, low effort):
- [ ] Batter stats cycling with name (AVG / HR / RBI) — add `batting` fields to `API_FIELDS` in `data/game.py`
- [ ] Last play description scroll — `currentPlay.result.description` already fetched, just not rendered
- [ ] Pitch count threshold color indicator at 80/100 pitches

Tier 2 (new API calls or meaningful new display):
- [ ] Exit velocity + distance flash on balls in play — add `hitData` to `API_FIELDS`
- [ ] Win probability bar — call `game_contextMetrics` endpoint
- [ ] Live scores board (all today's MLB games) — new plugin in `boards/` (see `boards/src/mlb_led_scoreboard_boards/clock.py`)

Tier 3 (most complex, most distinctive):
- [ ] Pitcher change "now pitching" card with season stats
- [ ] Scoring play recap flash when runs score

Suggested implementation order: play description → batter stats → exit velocity → pitch count color → live scores board → win probability → pitcher change card → scoring recap.

## Lower priority / cleanup

- [ ] **Fix disabled standings test assertions** — `standings/tests/test_standings.py` lines 87/92 have clinched/eliminated assertions commented out with "TODO reinstate after API updates".
