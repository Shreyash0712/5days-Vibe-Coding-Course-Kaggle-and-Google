import pytest
from pydantic import ValidationError
from app.agent import process_cart_checkout, CheckoutArgs, CARTS, DISCOUNT_CODES

def test_valid_checkout_no_discount():
    # Reset state
    CARTS["cart-test-1"] = {"user_id": "user-test-1", "total": 50.0, "status": "open"}
    args = CheckoutArgs(cart_id="cart-test-1", user_id="user-test-1")
    result = process_cart_checkout(args)
    assert "Successfully checked out" in result
    assert CARTS["cart-test-1"]["status"] == "completed"

def test_valid_checkout_with_discount():
    CARTS["cart-test-2"] = {"user_id": "user-test-2", "total": 50.0, "status": "open"}
    DISCOUNT_CODES["VALID20"] = {"redeemed": False, "user_id": None}
    args = CheckoutArgs(cart_id="cart-test-2", user_id="user-test-2", discount_code="VALID20")
    result = process_cart_checkout(args)
    assert "Successfully checked out" in result
    assert "VALID20" in result
    assert CARTS["cart-test-2"]["status"] == "completed"
    assert DISCOUNT_CODES["VALID20"]["redeemed"] is True

def test_invalid_cart_owner():
    CARTS["cart-test-3"] = {"user_id": "user-test-3", "total": 50.0, "status": "open"}
    args = CheckoutArgs(cart_id="cart-test-3", user_id="user-hacker-99")
    result = process_cart_checkout(args)
    assert "not authorized" in result
    assert CARTS["cart-test-3"]["status"] == "open"

def test_invalid_schema_injection():
    with pytest.raises(ValidationError):
        CheckoutArgs(cart_id="cart-123'; DROP TABLE users;", user_id="user-123")

def test_already_redeemed_discount():
    CARTS["cart-test-4"] = {"user_id": "user-test-4", "total": 50.0, "status": "open"}
    DISCOUNT_CODES["USED50"] = {"redeemed": True, "user_id": "some-other-user"}
    args = CheckoutArgs(cart_id="cart-test-4", user_id="user-test-4", discount_code="USED50")
    result = process_cart_checkout(args)
    assert "Checkout failed" in result
    assert "already been redeemed" in result
    assert CARTS["cart-test-4"]["status"] == "open"
