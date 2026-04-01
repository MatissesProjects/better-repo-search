using System;

public class Player {
    public float Health = 100f;
    public float MaxHealth = 100f;
    public float X = 0f;
    public float Y = 0f;
    public float Speed = 5f;

    public void calculate_player_health(float damage) {
        Health -= damage;
        if (Health < 0) Health = 0;
        Console.WriteLine($"Player took {damage} damage. Current Health: {Health}");
    }

    public void Move(float horizontal, float vertical) {
        X += horizontal * Speed;
        Y += vertical * Speed;
        Console.WriteLine($"Player moved to ({X}, {Y})");
    }

    public void Heal(float amount) {
        Health += amount;
        if (Health > MaxHealth) Health = MaxHealth;
        Console.WriteLine($"Player healed {amount}. Current Health: {Health}");
    }
}
