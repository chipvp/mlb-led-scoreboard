class Board:
    def __init__(self, renderer):
        self.renderer = renderer
        self.data = renderer.data

    def render(self, duration):
        raise NotImplementedError
