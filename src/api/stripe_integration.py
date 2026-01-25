"""
Stripe Integration for Takeoff.ai

Handles subscription checkout sessions, webhooks, and subscription management.
"""

import os
import stripe
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

# Initialize Stripe with API key from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Price IDs from Stripe Dashboard
PRICE_IDS = {
    "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_1SrsunFKb6Pa4iH5fwsIyemi"),
    "pro_annual": os.getenv("STRIPE_PRICE_PRO_ANNUAL", "price_1SrsunFKb6Pa4iH5nBVULeuf"),
    "agency_monthly": os.getenv("STRIPE_PRICE_AGENCY_MONTHLY", "price_1SrswrFKb6Pa4iH5dwowQve5"),
    "agency_annual": os.getenv("STRIPE_PRICE_AGENCY_ANNUAL", "price_1SrswrFKb6Pa4iH5PM1ubCpG"),
}

# Webhook secret for verifying Stripe events
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    AGENCY = "agency"


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class CheckoutSessionRequest(BaseModel):
    plan: str  # "pro" or "agency"
    interval: str  # "monthly" or "annual"
    success_url: str
    cancel_url: str
    customer_email: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class SubscriptionStatus(BaseModel):
    is_active: bool
    plan: str
    interval: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


class CustomerPortalResponse(BaseModel):
    portal_url: str


def get_price_id(plan: str, interval: str) -> str:
    """Get the Stripe Price ID for a given plan and interval."""
    key = f"{plan}_{interval}"
    price_id = PRICE_IDS.get(key)
    if not price_id:
        raise ValueError(f"Invalid plan/interval combination: {plan}/{interval}")
    return price_id


def create_checkout_session(
    plan: str,
    interval: str,
    success_url: str,
    cancel_url: str,
    customer_email: Optional[str] = None,
    client_reference_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Create a Stripe Checkout Session for subscription.
    
    Args:
        plan: "pro" or "agency"
        interval: "monthly" or "annual"
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if user cancels
        customer_email: Pre-fill customer email (optional)
        client_reference_id: Your internal user ID (optional)
    
    Returns:
        Dict with checkout_url and session_id
    """
    price_id = get_price_id(plan, interval)
    
    session_params = {
        "mode": "subscription",
        "payment_method_types": ["card"],
        "line_items": [
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": cancel_url,
        "allow_promotion_codes": True,  # Allow discount codes
        "billing_address_collection": "required",
        "metadata": {
            "plan": plan,
            "interval": interval,
        }
    }
    
    if customer_email:
        session_params["customer_email"] = customer_email
    
    if client_reference_id:
        session_params["client_reference_id"] = client_reference_id
    
    session = stripe.checkout.Session.create(**session_params)
    
    return {
        "checkout_url": session.url,
        "session_id": session.id
    }


def create_customer_portal_session(customer_id: str, return_url: str) -> str:
    """
    Create a Stripe Customer Portal session for managing subscription.
    
    Args:
        customer_id: Stripe Customer ID
        return_url: URL to redirect after portal session
    
    Returns:
        Portal URL
    """
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def get_subscription_from_session(session_id: str) -> Dict[str, Any]:
    """
    Retrieve subscription details from a completed checkout session.
    
    Args:
        session_id: Stripe Checkout Session ID
    
    Returns:
        Dict with subscription details
    """
    session = stripe.checkout.Session.retrieve(session_id)
    
    if session.subscription:
        subscription = stripe.Subscription.retrieve(session.subscription)
        return {
            "subscription_id": subscription.id,
            "customer_id": subscription.customer,
            "status": subscription.status,
            "plan": session.metadata.get("plan", "unknown"),
            "interval": session.metadata.get("interval", "unknown"),
            "current_period_end": datetime.fromtimestamp(
                subscription.current_period_end
            ).isoformat(),
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }
    
    return {"error": "No subscription found in session"}


def get_subscription_status(subscription_id: str) -> Dict[str, Any]:
    """
    Get the current status of a subscription.
    
    Args:
        subscription_id: Stripe Subscription ID
    
    Returns:
        Dict with subscription status details
    """
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Determine plan from price ID
        price_id = subscription["items"]["data"][0]["price"]["id"]
        plan = "free"
        interval = None
        
        for key, pid in PRICE_IDS.items():
            if pid == price_id:
                parts = key.split("_")
                plan = parts[0]
                interval = parts[1] if len(parts) > 1 else None
                break
        
        return {
            "is_active": subscription.status in ["active", "trialing"],
            "status": subscription.status,
            "plan": plan,
            "interval": interval,
            "current_period_end": datetime.fromtimestamp(
                subscription.current_period_end
            ).isoformat(),
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "customer_id": subscription.customer,
        }
    except stripe.error.StripeError as e:
        return {
            "is_active": False,
            "plan": "free",
            "error": str(e)
        }


def cancel_subscription(subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
    """
    Cancel a subscription.
    
    Args:
        subscription_id: Stripe Subscription ID
        at_period_end: If True, cancel at end of billing period. If False, cancel immediately.
    
    Returns:
        Dict with cancellation result
    """
    try:
        if at_period_end:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        else:
            subscription = stripe.Subscription.delete(subscription_id)
        
        return {
            "success": True,
            "status": subscription.status,
            "cancel_at_period_end": getattr(subscription, 'cancel_at_period_end', True),
        }
    except stripe.error.StripeError as e:
        return {
            "success": False,
            "error": str(e)
        }


def verify_webhook_signature(payload: bytes, signature: str) -> Dict[str, Any]:
    """
    Verify and parse a Stripe webhook event.
    
    Args:
        payload: Raw request body
        signature: Stripe-Signature header value
    
    Returns:
        Parsed event object
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, WEBHOOK_SECRET
        )
        return {"success": True, "event": event}
    except ValueError as e:
        return {"success": False, "error": f"Invalid payload: {str(e)}"}
    except stripe.error.SignatureVerificationError as e:
        return {"success": False, "error": f"Invalid signature: {str(e)}"}


def handle_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a Stripe webhook event.
    
    Args:
        event: Stripe event object
    
    Returns:
        Dict with handling result and any extracted data
    """
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    
    result = {
        "event_type": event_type,
        "handled": True,
    }
    
    if event_type == "checkout.session.completed":
        # New subscription created
        result["action"] = "subscription_created"
        result["customer_id"] = data.get("customer")
        result["subscription_id"] = data.get("subscription")
        # Get email from customer_email OR customer_details.email (Stripe sends it in different places)
        result["customer_email"] = data.get("customer_email") or data.get("customer_details", {}).get("email")
        result["plan"] = data.get("metadata", {}).get("plan")
        result["interval"] = data.get("metadata", {}).get("interval")
        
    elif event_type == "customer.subscription.updated":
        # Subscription updated (upgrade, downgrade, or renewal)
        result["action"] = "subscription_updated"
        result["subscription_id"] = data.get("id")
        result["customer_id"] = data.get("customer")
        result["status"] = data.get("status")
        result["cancel_at_period_end"] = data.get("cancel_at_period_end")
        
    elif event_type == "customer.subscription.deleted":
        # Subscription cancelled
        result["action"] = "subscription_cancelled"
        result["subscription_id"] = data.get("id")
        result["customer_id"] = data.get("customer")
        
    elif event_type == "invoice.payment_succeeded":
        # Successful payment (initial or renewal)
        result["action"] = "payment_succeeded"
        result["customer_id"] = data.get("customer")
        result["subscription_id"] = data.get("subscription")
        result["amount_paid"] = data.get("amount_paid", 0) / 100  # Convert from cents
        
    elif event_type == "invoice.payment_failed":
        # Failed payment
        result["action"] = "payment_failed"
        result["customer_id"] = data.get("customer")
        result["subscription_id"] = data.get("subscription")
        result["attempt_count"] = data.get("attempt_count")
        
    else:
        result["handled"] = False
        result["action"] = "unhandled_event"
    
    return result


# Pricing information for frontend display
PRICING_INFO = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "price_annual": 0,
        "estimates_per_month": 3,
        "features": [
            "3 estimates per month",
            "Basic room detection",
            "Watermarked PDF reports",
            "Standard materials only",
        ],
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 49,
        "price_annual": 490,
        "estimates_per_month": -1,  # Unlimited
        "features": [
            "Unlimited estimates",
            "Zip-code precision pricing",
            "Custom branding on PDFs",
            "All material categories",
            "Priority email support",
            "Export to Excel",
        ],
    },
    "agency": {
        "name": "Agency",
        "price_monthly": 149,
        "price_annual": 1490,
        "estimates_per_month": -1,  # Unlimited
        "features": [
            "Everything in Pro",
            "Team accounts (up to 5 users)",
            "White-label PDF reports",
            "API access",
            "Priority phone support",
            "Custom integrations",
        ],
    },
}


def get_pricing_info() -> Dict[str, Any]:
    """Get pricing information for all plans."""
    return PRICING_INFO
