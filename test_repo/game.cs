public class Game {
    private Player player = new Player();

    public void Update() {
        // Basic movement input simulation
        float moveX = 1.0f;
        float moveY = 0.0f;
        player.Move(moveX, moveY);

        // Simulate combat
        if (CheckForEnemies()) {
            player.calculate_player_health(10.5f);
        }
    }

    private bool CheckForEnemies() {
        return true; // Simplified for testing
    }
}
