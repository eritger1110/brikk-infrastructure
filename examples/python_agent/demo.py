#!/usr/bin/env python3
"""
Brikk Python Agent Demo
Demonstrates sending an echo job via the coordination protocol.
"""

import os
import sys
import json
import time
from client import BrikkClient


def main():
    """Run the demo agent."""
    print("🤖 Brikk Python Agent Demo")
    print("=" * 40)
    
    # Check for dry run mode
    dry_run = "--dry-run" in sys.argv or os.getenv("NO_NETWORK") == "1"
    
    try:
        if dry_run:
            # Use dummy credentials for dry run
            os.environ.setdefault("BRIKK_API_KEY", "demo-python-agent")
            os.environ.setdefault("BRIKK_SECRET", "demo-secret-key")
            os.environ.setdefault("BRIKK_BASE_URL", "http://localhost:5000")
        
        # Initialize client
        client = BrikkClient()
        print(f"✅ Connected to: {client.base_url}")
        print(f"🔑 Agent ID: {client.api_key}")
        
        if dry_run:
            print("🧪 Dry run mode - building envelope without network calls")
            
            # Build the coordination envelope
            recipient = "demo-echo-agent"
            payload = {
                "job_type": "echo",
                "message": "Hello from Python agent!",
                "data": {"test": True, "timestamp": 1234567890}
            }
            
            envelope = {
                "version": "1.0",
                "sender": client.api_key,
                "recipient": recipient,
                "payload": payload,
                "timestamp": int(time.time())
            }
            
            print(f"\n📦 Coordination envelope:")
            print(json.dumps(envelope, indent=2))
            print("✅ Demo envelope built successfully")
            return
        
        # Send echo job to a demo recipient
        recipient = "demo-echo-agent"
        payload = {
            "job_type": "echo",
            "message": "Hello from Python agent!",
            "data": {"test": True, "timestamp": 1234567890}
        }
        
        print(f"\n📤 Sending echo job to: {recipient}")
        print(f"📦 Payload: {payload}")
        
        # Send the message
        response = client.send(recipient, payload)
        
        print(f"\n✅ Response received:")
        print(f"📨 Status: {response.get('status', 'unknown')}")
        print(f"🆔 Message ID: {response.get('message_id', 'N/A')}")
        
        # Poll for any incoming messages
        messages = client.poll()
        print(f"\n📬 Polling result: {messages['status']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
