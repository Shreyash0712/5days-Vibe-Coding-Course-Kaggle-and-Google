# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from pydantic import BaseModel, Field

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id or "mock-project"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# In-memory store for discount codes.
DISCOUNT_CODES = {
    "WELCOME50": {"redeemed": False, "user_id": None},
    "SUMMER20": {"redeemed": False, "user_id": None},
}


class RedeemArgs(BaseModel):
    code: str = Field(..., max_length=20, pattern=r"^[a-zA-Z0-9]+$")
    user_id: str = Field(..., min_length=5, max_length=50, pattern=r"^[a-zA-Z0-9-_]+$")


def redeem_discount_code(args: RedeemArgs | dict) -> str:
    """Redeems a single-use discount code for a registered user.

    Args:
        args: The RedeemArgs containing the discount code and user_id.

    Returns:
        A message indicating success or failure.
    """
    if isinstance(args, dict):
        args = RedeemArgs(**args)

    code = args.code.upper()
    if code not in DISCOUNT_CODES:
        return f"Discount code '{code}' is invalid."

    code_info = DISCOUNT_CODES[code]
    if code_info["redeemed"]:
        return f"Discount code '{code}' has already been redeemed."

    code_info["redeemed"] = True
    code_info["user_id"] = args.user_id
    return f"Discount code '{code}' successfully redeemed for user {args.user_id}."


# In-memory store for carts
CARTS = {
    "cart-123": {"user_id": "user-456", "total": 100.0, "status": "open"}
}


class CheckoutArgs(BaseModel):
    cart_id: str = Field(..., min_length=5, max_length=50, pattern=r"^[a-zA-Z0-9-]+$")
    user_id: str = Field(..., min_length=5, max_length=50, pattern=r"^[a-zA-Z0-9-_]+$")
    discount_code: Optional[str] = Field(None, max_length=20, pattern=r"^[a-zA-Z0-9]*$")


def process_cart_checkout(args: CheckoutArgs | dict) -> str:
    """Processes a cart checkout for a user.

    Args:
        args: The CheckoutArgs containing cart_id, user_id, and an optional discount_code.

    Returns:
        A message indicating checkout success or failure.
    """
    if isinstance(args, dict):
        args = CheckoutArgs(**args)

    cart = CARTS.get(args.cart_id)
    if not cart:
        return f"Checkout failed: Cart '{args.cart_id}' not found."

    if cart["user_id"] != args.user_id:
        return f"Checkout failed: User '{args.user_id}' is not authorized to checkout cart '{args.cart_id}'."

    if cart["status"] != "open":
        return f"Checkout failed: Cart '{args.cart_id}' is already {cart['status']}."

    discount_message = ""
    if args.discount_code:
        redeem_args = RedeemArgs(code=args.discount_code, user_id=args.user_id)
        redeem_result = redeem_discount_code(redeem_args)
        if "successfully redeemed" not in redeem_result:
            return f"Checkout failed: {redeem_result}"
        discount_message = f" with discount code '{args.discount_code.upper()}' applied"

    cart["status"] = "completed"
    return f"Successfully checked out cart '{args.cart_id}' for user '{args.user_id}'{discount_message}. Total paid: ${cart['total']}."


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        api_key="AIzaSyD-mock-key-value-12345",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are an AI shopping assistant for a retail store. You help users with their shopping experience and can redeem discount codes for them.",
    tools=[redeem_discount_code, process_cart_checkout],
)

app = App(
    root_agent=root_agent,
    name="app",
)
