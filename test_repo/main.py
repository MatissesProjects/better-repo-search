from player import Player

def main():
    p = Player()
    
    print("--- Starting Python Demo ---")
    # Move the player
    p.move(1, 1)
    
    # Take some damage
    p.calculate_player_health(25)
    
    # Move again
    p.move(-1, 0)
    
    print(f"Final Position: ({p.x}, {p.y})")
    print(f"Final Health: {p.health}")

if __name__ == "__main__":
    main()
