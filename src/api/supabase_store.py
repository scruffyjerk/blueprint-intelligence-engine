"""
Supabase User Store for Takeoff.ai

Handles user profiles, subscriptions, and usage tracking via Supabase.
Replaces the in-memory JSON file storage with proper database persistence.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vfufkijlmzcvthzbigqy.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Initialize Supabase client (will be None if no service key)
supabase: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """Get or create Supabase client."""
    global supabase
    if supabase is None and SUPABASE_SERVICE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return supabase


class SupabaseUserStore:
    """User store backed by Supabase database."""
    
    def __init__(self):
        self.client = get_supabase_client()
        if not self.client:
            print("Warning: Supabase client not initialized. Check SUPABASE_SERVICE_KEY.")
    
    def _get_current_month(self) -> str:
        """Get current month in YYYY-MM format."""
        return datetime.now().strftime("%Y-%m")
    
    # =========================================================================
    # Profile Operations
    # =========================================================================
    
    def get_profile_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user profile by Supabase user ID."""
        if not self.client:
            return None
        try:
            result = self.client.table("profiles").select("*").eq("id", user_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def get_profile_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user profile by email."""
        if not self.client:
            return None
        try:
            result = self.client.table("profiles").select("*").eq("email", email.lower()).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting profile by email: {e}")
            return None
    
    def get_profile_by_stripe_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get a user profile by Stripe customer ID."""
        if not self.client:
            return None
        try:
            result = self.client.table("profiles").select("*").eq("stripe_customer_id", customer_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error getting profile by Stripe customer: {e}")
            return None
    
    def update_profile(self, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a user profile."""
        if not self.client:
            return None
        try:
            result = self.client.table("profiles").update(kwargs).eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating profile: {e}")
            return None
    
    def create_or_update_profile(self, user_id: str, email: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Create or update a user profile."""
        if not self.client:
            return None
        try:
            data = {"id": user_id, "email": email.lower(), **kwargs}
            result = self.client.table("profiles").upsert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating/updating profile: {e}")
            return None
    
    # =========================================================================
    # Subscription Operations
    # =========================================================================
    
    def get_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active subscription for a user."""
        if not self.client:
            return None
        try:
            result = self.client.table("subscriptions").select("*").eq("user_id", user_id).eq("status", "active").single().execute()
            return result.data
        except Exception as e:
            # No subscription found is not an error
            return None
    
    def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by Stripe subscription ID."""
        if not self.client:
            return None
        try:
            result = self.client.table("subscriptions").select("*").eq("stripe_subscription_id", stripe_subscription_id).single().execute()
            return result.data
        except Exception as e:
            return None
    
    def create_subscription(
        self,
        user_id: str,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        plan: str,
        billing_interval: str,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new subscription record."""
        if not self.client:
            return None
        try:
            data = {
                "user_id": user_id,
                "stripe_subscription_id": stripe_subscription_id,
                "stripe_customer_id": stripe_customer_id,
                "plan": plan,
                "status": "active",
                "billing_interval": billing_interval,
                "current_period_start": current_period_start.isoformat() if current_period_start else None,
                "current_period_end": current_period_end.isoformat() if current_period_end else None,
            }
            result = self.client.table("subscriptions").insert(data).execute()
            
            # Also update the profile plan
            self.update_profile(user_id, plan=plan, stripe_customer_id=stripe_customer_id)
            
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating subscription: {e}")
            return None
    
    def update_subscription(
        self,
        stripe_subscription_id: str,
        status: Optional[str] = None,
        plan: Optional[str] = None,
        cancel_at_period_end: Optional[bool] = None,
        current_period_end: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing subscription."""
        if not self.client:
            return None
        try:
            data = {}
            if status is not None:
                data["status"] = status
            if plan is not None:
                data["plan"] = plan
            if cancel_at_period_end is not None:
                data["cancel_at_period_end"] = cancel_at_period_end
            if current_period_end is not None:
                data["current_period_end"] = current_period_end.isoformat()
            
            if not data:
                return None
            
            result = self.client.table("subscriptions").update(data).eq("stripe_subscription_id", stripe_subscription_id).execute()
            
            # If plan changed, update profile too
            if plan and result.data:
                sub = result.data[0]
                self.update_profile(sub["user_id"], plan=plan)
            
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating subscription: {e}")
            return None
    
    def cancel_subscription(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """Cancel a subscription (mark as cancelled, revert user to free)."""
        if not self.client:
            return None
        try:
            # Get the subscription first to get user_id
            sub = self.get_subscription_by_stripe_id(stripe_subscription_id)
            if not sub:
                return None
            
            # Update subscription status
            result = self.client.table("subscriptions").update({
                "status": "cancelled"
            }).eq("stripe_subscription_id", stripe_subscription_id).execute()
            
            # Revert user to free plan
            self.update_profile(sub["user_id"], plan="free")
            
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error cancelling subscription: {e}")
            return None
    
    # =========================================================================
    # Usage Tracking
    # =========================================================================
    
    def get_usage(self, user_id: str) -> Dict[str, Any]:
        """Get current month's usage for a user."""
        if not self.client:
            return {"estimates_count": 0, "month_year": self._get_current_month()}
        
        try:
            month_year = self._get_current_month()
            result = self.client.table("usage").select("*").eq("user_id", user_id).eq("month_year", month_year).single().execute()
            return result.data if result.data else {"estimates_count": 0, "month_year": month_year}
        except Exception as e:
            return {"estimates_count": 0, "month_year": self._get_current_month()}
    
    def increment_usage(self, user_id: str) -> Dict[str, Any]:
        """Increment usage count for current month."""
        if not self.client:
            return {"allowed": True, "current_usage": 0, "limit": 3, "remaining": 3, "plan": "free"}
        
        try:
            month_year = self._get_current_month()
            
            # Get user's plan
            profile = self.get_profile_by_id(user_id)
            plan = profile.get("plan", "free") if profile else "free"
            
            # Get limits based on plan
            limits = {"free": 3, "pro": -1, "agency": -1}
            limit = limits.get(plan, 3)
            
            # Get current usage
            usage = self.get_usage(user_id)
            current_count = usage.get("estimates_count", 0)
            
            # Check if limit reached (before incrementing)
            if limit > 0 and current_count >= limit:
                return {
                    "allowed": False,
                    "current_usage": current_count,
                    "limit": limit,
                    "remaining": 0,
                    "plan": plan,
                    "message": f"Free tier limit reached ({limit} estimates/month). Upgrade to Pro for unlimited estimates."
                }
            
            # Increment usage (upsert)
            new_count = current_count + 1
            self.client.table("usage").upsert({
                "user_id": user_id,
                "month_year": month_year,
                "estimates_count": new_count
            }, on_conflict="user_id,month_year").execute()
            
            remaining = limit - new_count if limit > 0 else -1
            
            return {
                "allowed": True,
                "current_usage": new_count,
                "limit": limit,
                "remaining": remaining,
                "plan": plan,
            }
        except Exception as e:
            print(f"Error incrementing usage: {e}")
            return {"allowed": True, "current_usage": 0, "limit": 3, "remaining": 3, "plan": "free"}
    
    def check_usage(self, user_id: str) -> Dict[str, Any]:
        """Check usage without incrementing."""
        if not self.client:
            return {"current_usage": 0, "limit": 3, "remaining": 3, "plan": "free"}
        
        try:
            # Get user's plan
            profile = self.get_profile_by_id(user_id)
            plan = profile.get("plan", "free") if profile else "free"
            
            # Get limits
            limits = {"free": 3, "pro": -1, "agency": -1}
            limit = limits.get(plan, 3)
            
            # Get current usage
            usage = self.get_usage(user_id)
            current_count = usage.get("estimates_count", 0)
            
            remaining = limit - current_count if limit > 0 else -1
            
            return {
                "current_usage": current_count,
                "limit": limit,
                "remaining": remaining,
                "plan": plan,
            }
        except Exception as e:
            print(f"Error checking usage: {e}")
            return {"current_usage": 0, "limit": 3, "remaining": 3, "plan": "free"}
    
    # =========================================================================
    # Subscription Info (Combined)
    # =========================================================================
    
    def get_user_subscription_info(self, user_id: str) -> Dict[str, Any]:
        """Get complete subscription info for a user."""
        if not self.client:
            return {
                "plan": "free",
                "is_active": False,
                "estimates_remaining": 3,
            }
        
        try:
            # Get profile
            profile = self.get_profile_by_id(user_id)
            if not profile:
                return {
                    "plan": "free",
                    "is_active": False,
                    "estimates_remaining": 3,
                }
            
            # Get subscription
            subscription = self.get_subscription(user_id)
            
            # Get usage
            usage_info = self.check_usage(user_id)
            
            plan = profile.get("plan", "free")
            limits = {"free": 3, "pro": -1, "agency": -1}
            limit = limits.get(plan, 3)
            
            return {
                "plan": plan,
                "is_active": subscription.get("status") == "active" if subscription else False,
                "subscription_id": subscription.get("stripe_subscription_id") if subscription else None,
                "customer_id": profile.get("stripe_customer_id"),
                "current_period_end": subscription.get("current_period_end") if subscription else None,
                "cancel_at_period_end": subscription.get("cancel_at_period_end", False) if subscription else False,
                "billing_interval": subscription.get("billing_interval") if subscription else None,
                "estimates_this_month": usage_info.get("current_usage", 0),
                "estimates_limit": limit,
                "estimates_remaining": usage_info.get("remaining", 3),
            }
        except Exception as e:
            print(f"Error getting subscription info: {e}")
            return {
                "plan": "free",
                "is_active": False,
                "estimates_remaining": 3,
            }
    
    # =========================================================================
    # Webhook Handlers
    # =========================================================================
    
    def handle_checkout_completed(
        self,
        customer_id: str,
        customer_email: str,
        subscription_id: str,
        plan: str,
        interval: str,
        current_period_end: Optional[datetime] = None
    ) -> bool:
        """Handle checkout.session.completed webhook."""
        if not self.client:
            return False
        
        try:
            # Find user by email
            profile = self.get_profile_by_email(customer_email)
            
            if not profile:
                # User doesn't exist in profiles - this shouldn't happen if they signed up
                # But we'll handle it gracefully by logging
                print(f"Warning: No profile found for email {customer_email}")
                return False
            
            user_id = profile["id"]
            
            # Update profile with Stripe customer ID
            self.update_profile(user_id, stripe_customer_id=customer_id, plan=plan)
            
            # Create subscription record
            self.create_subscription(
                user_id=user_id,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
                plan=plan,
                billing_interval=interval,
                current_period_end=current_period_end
            )
            
            print(f"Checkout completed: {customer_email} -> {plan}")
            return True
            
        except Exception as e:
            print(f"Error handling checkout completed: {e}")
            return False
    
    def handle_subscription_updated(
        self,
        subscription_id: str,
        status: str,
        cancel_at_period_end: bool = False,
        current_period_end: Optional[datetime] = None
    ) -> bool:
        """Handle customer.subscription.updated webhook."""
        if not self.client:
            return False
        
        try:
            self.update_subscription(
                stripe_subscription_id=subscription_id,
                status=status,
                cancel_at_period_end=cancel_at_period_end,
                current_period_end=current_period_end
            )
            print(f"Subscription updated: {subscription_id} -> {status}")
            return True
        except Exception as e:
            print(f"Error handling subscription updated: {e}")
            return False
    
    def handle_subscription_deleted(self, subscription_id: str) -> bool:
        """Handle customer.subscription.deleted webhook."""
        if not self.client:
            return False
        
        try:
            self.cancel_subscription(subscription_id)
            print(f"Subscription cancelled: {subscription_id}")
            return True
        except Exception as e:
            print(f"Error handling subscription deleted: {e}")
            return False


# Global store instance
supabase_store = SupabaseUserStore()
