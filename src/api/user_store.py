"""
Simple In-Memory User Store for Takeoff.ai

This is a temporary solution for tracking users and usage.
In production, this should be replaced with Supabase or another database.

Note: Data is lost when the server restarts. This is intentional for the MVP.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

# File-based persistence (simple JSON file)
DATA_FILE = os.getenv("USER_DATA_FILE", "/tmp/takeoff_users.json")


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    AGENCY = "agency"


@dataclass
class User:
    """User data model."""
    id: str  # Could be email or Stripe customer ID
    email: str
    plan: str = "free"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: str = "inactive"
    subscription_interval: Optional[str] = None
    current_period_end: Optional[str] = None
    estimates_this_month: int = 0
    estimates_reset_date: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.estimates_reset_date:
            # Reset on the 1st of next month
            next_month = datetime.now().replace(day=1) + timedelta(days=32)
            self.estimates_reset_date = next_month.replace(day=1).isoformat()


class UserStore:
    """Simple in-memory user store with file persistence."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self._load_from_file()
    
    def _load_from_file(self):
        """Load users from JSON file if it exists."""
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    for user_id, user_data in data.items():
                        self.users[user_id] = User(**user_data)
        except Exception as e:
            print(f"Warning: Could not load user data: {e}")
    
    def _save_to_file(self):
        """Save users to JSON file."""
        try:
            data = {uid: asdict(user) for uid, user in self.users.items()}
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save user data: {e}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None
    
    def get_user_by_stripe_customer(self, customer_id: str) -> Optional[User]:
        """Get a user by Stripe customer ID."""
        for user in self.users.values():
            if user.stripe_customer_id == customer_id:
                return user
        return None
    
    def create_user(self, email: str, **kwargs) -> User:
        """Create a new user."""
        user_id = email.lower()  # Use email as ID for simplicity
        
        if user_id in self.users:
            return self.users[user_id]
        
        user = User(id=user_id, email=email, **kwargs)
        self.users[user_id] = user
        self._save_to_file()
        return user
    
    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update a user's data."""
        user = self.users.get(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.now().isoformat()
        self._save_to_file()
        return user
    
    def update_subscription(
        self,
        user_id: str,
        plan: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        subscription_status: str = "active",
        subscription_interval: Optional[str] = None,
        current_period_end: Optional[str] = None
    ) -> Optional[User]:
        """Update a user's subscription details."""
        return self.update_user(
            user_id,
            plan=plan,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            subscription_status=subscription_status,
            subscription_interval=subscription_interval,
            current_period_end=current_period_end
        )
    
    def cancel_subscription(self, user_id: str) -> Optional[User]:
        """Cancel a user's subscription (revert to free)."""
        return self.update_user(
            user_id,
            plan="free",
            subscription_status="cancelled",
            stripe_subscription_id=None
        )
    
    def increment_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Increment a user's estimate count for the month.
        
        Returns:
            Dict with usage info and whether limit is reached
        """
        user = self.users.get(user_id)
        if not user:
            # Create anonymous user for tracking
            user = self.create_user(email=user_id)
        
        # Check if we need to reset the counter (new month)
        if user.estimates_reset_date:
            reset_date = datetime.fromisoformat(user.estimates_reset_date)
            if datetime.now() >= reset_date:
                user.estimates_this_month = 0
                # Set next reset date
                next_month = datetime.now().replace(day=1) + timedelta(days=32)
                user.estimates_reset_date = next_month.replace(day=1).isoformat()
        
        # Get limit based on plan
        limits = {
            "free": 3,
            "pro": -1,  # Unlimited
            "agency": -1,  # Unlimited
        }
        limit = limits.get(user.plan, 3)
        
        # Check if limit reached (before incrementing)
        if limit > 0 and user.estimates_this_month >= limit:
            return {
                "allowed": False,
                "current_usage": user.estimates_this_month,
                "limit": limit,
                "plan": user.plan,
                "message": f"Free tier limit reached ({limit} estimates/month). Upgrade to Pro for unlimited estimates."
            }
        
        # Increment usage
        user.estimates_this_month += 1
        user.updated_at = datetime.now().isoformat()
        self._save_to_file()
        
        remaining = limit - user.estimates_this_month if limit > 0 else -1
        
        return {
            "allowed": True,
            "current_usage": user.estimates_this_month,
            "limit": limit,
            "remaining": remaining,
            "plan": user.plan,
        }
    
    def check_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Check a user's current usage without incrementing.
        
        Returns:
            Dict with usage info
        """
        user = self.users.get(user_id)
        if not user:
            return {
                "current_usage": 0,
                "limit": 3,
                "remaining": 3,
                "plan": "free",
            }
        
        limits = {
            "free": 3,
            "pro": -1,
            "agency": -1,
        }
        limit = limits.get(user.plan, 3)
        remaining = limit - user.estimates_this_month if limit > 0 else -1
        
        return {
            "current_usage": user.estimates_this_month,
            "limit": limit,
            "remaining": remaining,
            "plan": user.plan,
            "reset_date": user.estimates_reset_date,
        }
    
    def get_user_subscription_info(self, user_id: str) -> Dict[str, Any]:
        """Get subscription info for a user."""
        user = self.users.get(user_id)
        if not user:
            return {
                "plan": "free",
                "is_active": False,
                "estimates_remaining": 3,
            }
        
        limits = {"free": 3, "pro": -1, "agency": -1}
        limit = limits.get(user.plan, 3)
        remaining = limit - user.estimates_this_month if limit > 0 else -1
        
        return {
            "plan": user.plan,
            "is_active": user.subscription_status == "active",
            "subscription_id": user.stripe_subscription_id,
            "customer_id": user.stripe_customer_id,
            "current_period_end": user.current_period_end,
            "estimates_this_month": user.estimates_this_month,
            "estimates_limit": limit,
            "estimates_remaining": remaining,
        }


# Global store instance
user_store = UserStore()
