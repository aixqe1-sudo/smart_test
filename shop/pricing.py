from shop.cart import Item, subtotal

def total(items: list[Item], discount_percent: int = 0) -> float:
    if not 0 <= discount_percent <= 100:
        raise ValueError("Discount must be between 0 and 100")
    return round(subtotal(items) * (100 - discount_percent) / 100, 2)
