from shop.cart import Item, subtotal

def test_subtotal_two_items():
    assert subtotal([Item("book", 20, 2), Item("pen", 5)]) == 45

def test_invalid_quantity():
    import pytest
    with pytest.raises(ValueError):
        subtotal([Item("book", 20, 0)])
