# TODO

## Bigger features

- [x] **Per-team spoiler switches** — replace the single global "Spoiler Free" HomeKit switch with multiple switches: one per preferred team (e.g. Cubs, Angels) that enables spoiler-free mode for just that team's games, plus a general "Spoiler Mode" switch that hides scores for all teams. Currently `homekit_server.py` exposes one `SpoilerModeAccessory` and `spoiler_mode_manager.py` stores a single global bool (`is_spoiler_mode()`); `renderers/main.py:106` gates on `spoiler_mode_manager.is_spoiler_mode() and is_preferred_game`. Needs `spoiler_mode_manager` to track per-team state (e.g. a set/dict of team abbreviations plus a global flag) and `homekit_server.py` to dynamically create one accessory per preferred team plus the global one.
- [ ] **Linescore display** — inning-by-inning run totals for live/final games.
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
- [ ] Live scores board (all today's MLB games) — new `boards/scores.py` board type

Tier 3 (most complex, most distinctive):
- [ ] Pitcher change "now pitching" card with season stats
- [ ] Scoring play recap flash when runs score

Suggested implementation order: play description → batter stats → exit velocity → pitch count color → live scores board → win probability → pitcher change card → scoring recap.

## Lower priority / cleanup

- [ ] **Fix disabled standings test assertions** — `tests/test_standings.py` lines 87/92 have clinched/eliminated assertions commented out with "TODO reinstate after API updates".
- [ ] **Network error sentinel** — `data/__init__.py` uses `self.weather.conditions == "Error"` as network issues flag; brittle string match. Use explicit bool.
- [ ] **WBC schedule resilience** — `data/schedule.py` fetches MLB + WBC in one call; WBC slowness/errors fail the whole schedule refresh.
