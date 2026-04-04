package com.example;

import java.util.List;

public class GameSession {
    private List<String> players;

    public void start() {
        System.out.println("Game started!");
    }

    public List<String> getPlayers() {
        return players;
    }
}
