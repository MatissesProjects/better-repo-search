class Player:
    def __init__(self):
        self.health = 100.0
        self.max_health = 100.0
        self.x = 0.0
        self.y = 0.0
        self.speed = 5.0

    def calculate_player_health(self, damage):
        """Calculates health after taking damage and handles death state."""
        self.health -= damage
        if self.health < 0:
            self.health = 0
        print(f"Python Player took {damage} damage. Health: {self.health}")

    def move(self, dx, dy):
        """Updates player position based on movement vector."""
        self.x += dx * self.speed
        self.y += dy * self.speed
        print(f"Python Player moved to ({self.x}, {self.y})")

    def reset_position(self):
        self.x = 0.0
        self.y = 0.0
