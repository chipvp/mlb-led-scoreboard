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

    away_color = colors.graphics_color("linescore.away")
    home_color = colors.graphics_color("linescore.home")
    header_color = colors.graphics_color("linescore.header")
    empty_color = colors.graphics_color("linescore.empty")
    bg_color = colors.graphics_color("linescore.background")

    total_innings = max(scoreboard.inning.number, innings_to_show)
    start_inning = total_innings - innings_to_show + 1

    # Column start positions. Columns are only widened for double-digit inning
    # numbers when a header row is shown — that's the only thing that needs the
    # extra room. Without a header, extra-inning games would otherwise get
    # uneven gaps between columns for no visual reason.
    header = coords.get("header")
    header_enabled = bool(header and "y" in header)
    char_width = font["size"]["width"]
    if header_enabled:
        digit_counts = [len(str(start_inning + i)) for i in range(innings_to_show)]
    else:
        digit_counts = [1] * innings_to_show
    bg = coords.get("background")
    if bg:
        available_width = (bg["x"] + bg["width"]) - innings_x
        total_units = sum(digit_counts)
        col_x = []
        cum_units = 0
        for digits in digit_counts:
            col_x.append(innings_x + round(available_width * cum_units / total_units))
            cum_units += digits
    else:
        col_x = []
        x = innings_x
        for digits in digit_counts:
            col_x.append(x)
            x += max(col_width, digits * char_width + 1)

    # Draw green background over the linescore area
    if bg:
        for row in range(bg["height"]):
            graphics.DrawLine(canvas, bg["x"], bg["y"] + row, bg["x"] + bg["width"], bg["y"] + row, bg_color)

    # Optional inning-number header row
    if header_enabled:
        for i in range(innings_to_show):
            graphics.DrawText(canvas, font["font"], col_x[i], header["y"], header_color, str(start_inning + i))

    _draw_row(
        canvas, font, away_color, empty_color,
        coords["away"]["y"], scoreboard.away_team.abbrev,
        scoreboard.linescore.away_innings,
        show_team, team_x, col_x, innings_to_show, start_inning, char_width, digit_counts,
    )
    _draw_row(
        canvas, font, home_color, empty_color,
        coords["home"]["y"], scoreboard.home_team.abbrev,
        scoreboard.linescore.home_innings,
        show_team, team_x, col_x, innings_to_show, start_inning, char_width, digit_counts,
    )


def _draw_row(canvas, font, color, empty_color, y, abbrev, inning_runs,
              show_team, team_x, col_x, innings_to_show, start_inning, char_width, digit_counts):
    if show_team:
        graphics.DrawText(canvas, font["font"], team_x, y, color, abbrev[:3].upper())

    for i in range(innings_to_show):
        inning_index = start_inning + i - 1
        # right-justify under the ones digit once the header number goes to two digits
        x = col_x[i] + (digit_counts[i] - 1) * char_width
        if 0 <= inning_index < len(inning_runs) and inning_runs[inning_index] is not None:
            val = inning_runs[inning_index]
            text = str(val) if val < 10 else "X"
            graphics.DrawText(canvas, font["font"], x, y, color, text)
        else:
            graphics.DrawText(canvas, font["font"], x, y, empty_color, "-")
