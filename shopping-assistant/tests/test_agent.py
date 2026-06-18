import pytest
from pydantic import ValidationError
from app.agent import redeem_discount_code, RedeemArgs, DISCOUNT_CODES

def test_redeem_valid_code():
    DISCOUNT_CODES["TEST10"] = {"redeemed": False, "user_id": None}
    args = RedeemArgs(code="TEST10", user_id="user-123")
    result = redeem_discount_code(args)
    assert "successfully redeemed" in result
    assert DISCOUNT_CODES["TEST10"]["redeemed"] is True
    assert DISCOUNT_CODES["TEST10"]["user_id"] == "user-123"

def test_redeem_invalid_code():
    args = RedeemArgs(code="INVALID99", user_id="user-123")
    result = redeem_discount_code(args)
    assert "is invalid" in result

def test_redeem_already_redeemed_code():
    DISCOUNT_CODES["USED10"] = {"redeemed": True, "user_id": "old-user"}
    args = RedeemArgs(code="USED10", user_id="user-123")
    result = redeem_discount_code(args)
    assert "already been redeemed" in result
    assert DISCOUNT_CODES["USED10"]["user_id"] == "old-user"

def test_schema_injection_rejection():
    # Attempting to pass malformed SQL injection string
    with pytest.raises(ValidationError):
        RedeemArgs(code="CODE123'; DROP TABLE", user_id="user-123")

def test_schema_length_rejection():
    # Attempting to pass overly long string for Denial of Service / Buffer Overflow
    with pytest.raises(ValidationError):
        RedeemArgs(code="A" * 50, user_id="user-123")
