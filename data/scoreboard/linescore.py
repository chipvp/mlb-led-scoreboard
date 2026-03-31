from data.game import Game


class Linescore:
    def __init__(self, game: Game):
        self.away_innings = game.inning_runs("away")
        self.home_innings = game.inning_runs("home")
