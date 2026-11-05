"""Risk rules are dynamically loaded by checkout; static import graphs cannot see this."""

def allowed_for_checkout(amount: float) -> bool:
    return amount <= 500
