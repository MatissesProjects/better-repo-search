interface Entity {
    id: string;
}

class Player implements Entity {
    id: string;
    health: number = 100;

    constructor(id: string) {
        this.id = id;
    }

    takeDamage(amount: number): void {
        this.health -= amount;
        if (this.health < 0) this.health = 0;
    }
}

const p = new Player("p1");
p.takeDamage(20);
