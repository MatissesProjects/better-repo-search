package com.example

import kotlin.math.*

class Warrior(val name: String) {
    var health: Int = 100

    fun attack(target: String) {
        println("$name is attacking $target")
    }
}

fun main() {
    val w = Warrior("Gimli")
    w.attack("Orc")
}
