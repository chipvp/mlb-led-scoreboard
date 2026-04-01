class Board:
    def __init__(self, renderer):
        self.renderer = renderer
        self.data = renderer.data
        self.item_duration = None  # optional per-item duration, set by run_boards

    def render(self, duration):
        raise NotImplementedError
