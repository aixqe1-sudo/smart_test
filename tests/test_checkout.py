from shop.cart import Item
from shop.checkout import place_order

def test_small_order_accepted():
    assert place_order([Item("pen", 10)])["status"] == "accepted"

def test_large_order_rejected():
    assert place_order([Item("laptop", 750)])["status"] == "rejected"

def test_discount_makes_order_eligible():
    assert place_order([Item("laptop", 600)], 20)["status"] == "accepted"
