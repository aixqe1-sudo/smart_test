from dataclasses import dataclass

@dataclass(frozen=True)
class Item:
    sku: str
    price: float
    quantity: int = 1

def subtotal(items: list[Item]) -> float:
    if any(item.price < 0 or item.quantity < 1 for item in items):
        raise ValueError("Invalid cart item")
    return round(sum(item.price * item.quantity for item in items), 2)
