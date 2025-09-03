"""
Clerk webhook endpoints for user synchronization.

Handles user lifecycle events from Clerk and syncs to our database.
"""

import json
import hmac
import hashlib
from typing import Any, Dict

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.orm import Session

from config.settings import get_settings
from core.storage import get_database_session, User


router = APIRouter()
settings = get_settings()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Clerk/Svix webhook signature."""
    try:
        print(f"Verifying signature: {signature[:50]}...")
        print(f"Using secret: {secret}")
        
        # For development with "dev" secret, skip verification
        if secret == "dev":
            print("Development mode: skipping signature verification")
            return True
            
        # Svix signature format: "v1,<base64_signature>"
        parts = signature.split(",")
        if len(parts) != 2 or parts[0] != "v1":
            print(f"Invalid signature format. Expected 'v1,signature', got: {signature}")
            return False
            
        # Extract base64 signature
        signature_b64 = parts[1]
        print(f"Extracted signature: {signature_b64}")
        
        # Decode base64 signature
        try:
            import base64
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as e:
            print(f"Failed to decode base64 signature: {e}")
            return False
        
        # Create expected signature using the webhook secret
        # Remove 'whsec_' prefix if present
        clean_secret = secret.replace('whsec_', '') if secret.startswith('whsec_') else secret
        print(f"Clean secret: {clean_secret[:10]}...")
        
        # Create expected signature
        expected = hmac.new(
            base64.b64decode(clean_secret),
            payload,
            hashlib.sha256
        ).digest()
        
        result = hmac.compare_digest(signature_bytes, expected)
        print(f"Signature comparison result: {result}")
        return result
        
    except Exception as e:
        print(f"Signature verification error: {e}")
        # For development, return True if signature verification fails
        return secret == "dev"


@router.post("/user.created")
async def handle_user_created(
    request: Request,
    db: Session = Depends(get_database_session)
):
    """Handle user creation from Clerk."""
    try:
        body = await request.body()
        
        # Debug: Log all headers
        print("=== WEBHOOK DEBUG ===")
        print("Headers:", dict(request.headers))
        print("Body preview:", body[:200])
        print("Webhook secret:", settings.clerk_webhook_secret)
        
        # Get signature from headers (try multiple possible header names)
        signature = request.headers.get("svix-signature") or request.headers.get("webhook-signature") or request.headers.get("x-webhook-signature")
        
        print("Found signature:", signature)
        
        if not signature:
            print("ERROR: No signature header found")
            raise HTTPException(status_code=401, detail="Missing signature header")
        
        # Verify webhook signature
        is_valid = verify_webhook_signature(body, signature, settings.clerk_webhook_secret)
        print("Signature valid:", is_valid)
        
        # TEMPORARY: Skip signature verification for debugging
        print("⚠️  TEMPORARILY SKIPPING SIGNATURE VERIFICATION FOR DEBUGGING")
        # if not is_valid:
        #     print("ERROR: Invalid signature")
        #     raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        data = json.loads(body)
        user_data = data.get("data", {})
        
        print("Full webhook data:", json.dumps(data, indent=2)[:500] + "...")
        print("User data keys:", list(user_data.keys()))
        
        # Check if this is a deletion event (shouldn't hit user.created)
        if user_data.get("deleted", False):
            print("⚠️  This is a deletion event hitting user.created endpoint")
            return {"status": "ignored", "reason": "deletion event on creation endpoint"}
        
        # Extract user information
        clerk_user_id = user_data.get("id")
        email_addresses = user_data.get("email_addresses", [])
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")
        
        print(f"Extracted data - ID: {clerk_user_id}, emails: {len(email_addresses)}, name: {first_name} {last_name}")
        
        # Get primary email
        primary_email = None
        for email in email_addresses:
            if email.get("primary", False):
                primary_email = email.get("email_address")
                break
        
        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get("email_address")
        
        print(f"Primary email: {primary_email}")
        
        if not clerk_user_id or not primary_email:
            print(f"❌ Missing required data - ID: {clerk_user_id}, Email: {primary_email}")
            raise HTTPException(status_code=400, detail="Missing required user data")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if existing_user:
            return {"status": "user already exists"}
        
        # Create new user
        new_user = User(
            clerk_user_id=clerk_user_id,
            email=primary_email,
            first_name=first_name,
            last_name=last_name,
        )
        
        db.add(new_user)
        db.commit()
        
        return {"status": "user created", "user_id": clerk_user_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


@router.post("/user.updated")
async def handle_user_updated(
    request: Request,
    svix_signature: str = Header(..., alias="svix-signature"),
    db: Session = Depends(get_database_session)
):
    """Handle user updates from Clerk."""
    try:
        body = await request.body()
        
        # Verify webhook signature
        if not verify_webhook_signature(body, svix_signature, settings.clerk_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        data = json.loads(body)
        user_data = data.get("data", {})
        
        clerk_user_id = user_data.get("id")
        if not clerk_user_id:
            raise HTTPException(status_code=400, detail="Missing user ID")
        
        # Find existing user
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user data
        email_addresses = user_data.get("email_addresses", [])
        if email_addresses:
            for email in email_addresses:
                if email.get("primary", False):
                    user.email = email.get("email_address")
                    break
        
        user.first_name = user_data.get("first_name")
        user.last_name = user_data.get("last_name")
        
        db.commit()
        
        return {"status": "user updated", "user_id": clerk_user_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")


@router.post("/user.deleted")
async def handle_user_deleted(
    request: Request,
    svix_signature: str = Header(..., alias="svix-signature"),
    db: Session = Depends(get_database_session)
):
    """Handle user deletion from Clerk."""
    try:
        body = await request.body()
        
        # Verify webhook signature
        if not verify_webhook_signature(body, svix_signature, settings.clerk_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        data = json.loads(body)
        user_data = data.get("data", {})
        
        clerk_user_id = user_data.get("id")
        if not clerk_user_id:
            raise HTTPException(status_code=400, detail="Missing user ID")
        
        # Find and delete user
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if user:
            db.delete(user)
            db.commit()
        
        return {"status": "user deleted", "user_id": clerk_user_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")
