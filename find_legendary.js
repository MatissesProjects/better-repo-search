import math

def mulberry32(seed):
    a = seed & 0xFFFFFFFF
    def rng():
        nonlocal a
        a = (a + 0x6d2b79f5) & 0xFFFFFFFF
        t = (a ^ (a >> 15)) * (1 | a)
        t = (t & 0xFFFFFFFF)
        t = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
        t = (t ^ t) ^ t # Just to be safe with python's large ints
        # Wait, the JS implementation is:
        # t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
        # return ((t ^ (t >>> 14)) >>> 0) / 4294967296
        return None
    
    # Let's rewrite strictly matching JS behavior with imul
    def imul(a, b):
        return (a * b) & 0xFFFFFFFF
        
    def rng_js():
        nonlocal a
        a = (a + 0x6d2b79f5) & 0xFFFFFFFF
        t = (a ^ (a >> 15)) * (1 | a)
        t &= 0xFFFFFFFF
        # JS: t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
        t = (t + imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF
        t ^= t # wait, the snippet says: (t + Math.imul(...)) ^ t
        # Let's look at the snippet again: 
        # t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
        # return ((t ^ (t >>> 14)) >>> 0) / 4294967296
        
    return None

# Actually, let's just write a small Node.js script since the logic is in JS anyway.
# It's much easier to match the exact bitwise behavior of JS in JS.
