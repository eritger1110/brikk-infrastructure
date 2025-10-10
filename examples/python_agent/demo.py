#!/usr/bin/env python3
"""
Brikk Python Agent Demo
Demonstrates sending an echo job via the coordination protocol.
"""

import json
import os
import sys
import time
from client import BrikkClient  # assumes examples/python_agent/client.py

def main():
    print("ğŸ¤- Brikk Python Agent Demo")
    print("=" * 40)

    dry_run = ("--dry-run" in sys.argv) or (os.getenv("NO_NETWORK") == "1")

    try:
        if dry_run:
            # Safe dummy defaults so the script runs offline
            os.environ.setdefault("BRIKK_API_KEY", "demo-python-agent")
            os.environ.setdefault("BRIKK_SECRET", "demo-secret-key")
            os.environ.setdefault("BRIKK_BASE_URL", "http://localhost:5000")

        client = BrikkClient()
        print(f"âœ... Connected to: {client.base_url}")
        print(f"ğŸ"' Agent ID: {client.api_key}")

        recipient = "demo-echo-agent"
        payload = {
            "job_type": "echo",
            "message": "Hello from Python agent!",
            "data": {"test": True, "timestamp": 1234567890},
        }

        if dry_run:
            print("ğŸ§ª Dry run mode - building envelope without network calls")
            envelope = {
                "version": "1.0",
                "sender": client.api_key,
                "recipient": recipient,
                "payload": payload,
                "timestamp": int(time.time()),
            }
            print("\nğŸ"¦ Coordination envelope:")
            print(json.dumps(envelope, indent=2))
            print("âœ... Demo envelope built successfully")
            return

        print(f"\nğŸ"¤ Sending echo job to: {recipient}")
        print("ğŸ"¦ Payload:", payload)
        response = client.send(recipient, payload)

        print("\nâœ... Response received:")
        print(f"ğŸ"¨ Status: {response.get('status', 'unknown')}")
        print(f"ğŸ†" Message ID: {response.get('message_id', 'N/A')}")

        messages = client.poll()
        print(f"\nğŸ"¬ Polling result: {messages.get('status')}")
    except Exception as e:
        print(f"âŒ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
