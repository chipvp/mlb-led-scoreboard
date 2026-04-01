import debug


def run_boards(renderer, board_names, rotation_rate):
    from boards.clock import ClockBoard
    from boards.countdown import CountdownBoard
    from boards.news import NewsBoard
    from boards.scores import ScoresBoard
    from boards.standings import StandingsBoard
    from boards.weather import WeatherBoard

    board_registry = {
        "clock": ClockBoard,
        "countdown": CountdownBoard,
        "weather": WeatherBoard,
        "standings": StandingsBoard,
        "news": NewsBoard,
        "scores": ScoresBoard,
    }

    for entry in board_names:
        if isinstance(entry, dict):
            name = entry.get("name")
            duration = entry.get("duration", rotation_rate)
        else:
            name = entry
            duration = rotation_rate
        cls = board_registry.get(name)
        if cls is None:
            debug.warning("Unknown board type: '%s' — skipping", name)
            continue
        cls(renderer).render(duration)
