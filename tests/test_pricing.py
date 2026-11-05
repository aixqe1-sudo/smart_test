import pytest
from shop.cart import Item
from shop.pricing import total

def test_discount():
    assert total([Item("book", 100)], 10) == 90

def test_discount_out_of_range():
    with pytest.raises(ValueError):
        total([Item("book", 100)], 101)
