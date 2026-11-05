from importlib import import_module
from shop.cart import Item
from shop.pricing import total

def place_order(items: list[Item], discount_percent: int = 0) -> dict:
    amount = total(items, discount_percent)
    # Deliberately dynamic dependency: invisible to ordinary AST import walking.
    risk = import_module("shop.risk")
    if not risk.allowed_for_checkout(amount):
        return {"status": "rejected", "amount": amount}
    return {"status": "accepted", "amount": amount}
