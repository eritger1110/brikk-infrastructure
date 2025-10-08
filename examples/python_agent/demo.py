#!/usr/bin/env python3
"""
Brikk Python Agent Demo
Demonstrates sending an echo job via the coordination protocol.
"""

import os
import sys
from client import BrikkClient


def main():
    """Run the demo agent."""
    print("🤖 Brikk Python Agent Demo")
    print("=" * 40)
    
    # Check for dry run mode
    dry_run = "--dry-run" in sys.argv
    
    try:
        # Initialize client
        client = BrikkClient()
        print(f"✅ Connected to: {client.base_url}")
        print(f"🔑 Agent ID: {client.api_key}")
        
        if dry_run:
            print("🧪 Dry run mode - skipping network calls")
            print("✅ Demo would send echo job successfully")
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
