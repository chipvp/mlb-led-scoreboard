from driver import graphics


def render_linescore(canvas, layout, colors, scoreboard):
    try:
        coords = layout.coords("linescore")
    except KeyError:
        return

    if not coords.get("enabled", False):
        return

    font = layout.font("linescore")
    col_width = coords.get("column_width", font["size"]["width"] + 1)
    innings_to_show = coords.get("innings", 9)
    show_team = coords.get("show_team", True)
    team_x = coords.get("team_abbrev_x", 0)
    innings_x = coords.get("innings_start_x", team_x + font["size"]["width"] * 4)
    total_x = coords.get("total_x", innings_x + innings_to_show * col_width + 1)

    away_color = colors.graphics_color("linescore.away")
    home_color = colors.graphics_color("linescore.home")
    header_color = colors.graphics_color("linescore.header")
    empty_color = colors.graphics_color("linescore.empty")
    bg_color = colors.graphics_color("linescore.background")

    # Draw green background over the linescore area
    bg = coords.get("background")
    if bg:
        for row in range(bg["height"]):
            graphics.DrawLine(canvas, bg["x"], bg["y"] + row, bg["x"] + bg["width"], bg["y"] + row, bg_color)

    # Optional inning-number header row
    header = coords.get("header")
    if header and "y" in header:
        hx = innings_x
        for i in range(innings_to_show):
            graphics.DrawText(canvas, font["font"], hx, header["y"], header_color, str(i + 1))
            hx += col_width
        graphics.DrawText(canvas, font["font"], total_x, header["y"], header_color, "R")

    _draw_row(
        canvas, font, away_color, empty_color,
        coords["away"]["y"], scoreboard.away_team.abbrev,
        scoreboard.linescore.away_innings, scoreboard.away_team.runs,
        show_team, team_x, innings_x, col_width, total_x, innings_to_show,
    )
    _draw_row(
        canvas, font, home_color, empty_color,
        coords["home"]["y"], scoreboard.home_team.abbrev,
        scoreboard.linescore.home_innings, scoreboard.home_team.runs,
        show_team, team_x, innings_x, col_width, total_x, innings_to_show,
    )


def _draw_row(canvas, font, color, empty_color, y, abbrev, inning_runs, total_runs,
              show_team, team_x, innings_x, col_width, total_x, innings_to_show):
    if show_team:
        graphics.DrawText(canvas, font["font"], team_x, y, color, abbrev[:3].upper())

    x = innings_x
    for i in range(innings_to_show):
        if i < len(inning_runs) and inning_runs[i] is not None:
            val = inning_runs[i]
            text = str(val) if val < 10 else "X"
            graphics.DrawText(canvas, font["font"], x, y, color, text)
        else:
            graphics.DrawText(canvas, font["font"], x, y, empty_color, "-")
        x += col_width

    graphics.DrawText(canvas, font["font"], total_x, y, color, str(total_runs))
