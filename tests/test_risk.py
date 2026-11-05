from shop.risk import allowed_for_checkout

def test_small_amount_allowed():
    assert allowed_for_checkout(100)

def test_boundary_amount_allowed():
    assert allowed_for_checkout(500)
