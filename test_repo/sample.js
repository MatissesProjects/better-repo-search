function calculateDamage(base, armor) {
    return base * (1 - armor / 100);
}

class User {
    constructor(name) {
        this.name = name;
    }
    
    getName() {
        return this.name;
    }
}

const u = new User("Alice");
console.log(u.getName());
console.log(calculateDamage(10, 5));
