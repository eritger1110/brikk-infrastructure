"""
Brikk Python SDK Quickstart Example

This script demonstrates the core functionality of the Brikk Python SDK.

To run this example:
1. Install the SDK: `pip install -e sdk/python`
2. Set environment variables:
   - `BRIKK_BASE_URL`: Your Brikk API base URL (e.g., http://localhost:8000)
   - `BRIKK_API_KEY`: Your API key
   - `BRIKK_SIGNING_SECRET`: Your signing secret for HMAC auth
   - `BRIKK_ORG_ID`: Your organization ID
3. Run the script: `python examples/sdk/python_quickstart.py`
"""

import os
import asyncio
from brikk import BrikkClient, BrikkError


async def main():
    """Main function to demonstrate SDK functionality."""
    print("--- Brikk Python SDK Quickstart ---")

    # 1. Initialize the client from environment variables
    try:
        client = BrikkClient()
        print(f"[OK] Client initialized for base URL: {client.base_url}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize client: {e}")
        return

    org_id = client.org_id
    if not org_id:
        print("[ERROR] BRIKK_ORG_ID environment variable not set. Aborting.")
        return

    try:
        # 2. Check API health
        print("\nPinging health check endpoint...")
        health = await client.health.ping()
        print(f"[OK] Health status: {health.get('status')}")

        # 3. Create a new agent (or use an existing one)
        print("\nCreating or getting an agent...")
        agent_name = "My Python SDK Agent"
        try:
            agent = await client.agents.create(name=agent_name, org_id=org_id)
            print(f"[OK] Created new agent: {agent['name']} (ID: {agent['id']})")
        except BrikkError as e:
            if e.status_code == 409:  # Conflict, agent likely exists
                agents = await client.agents.list(org_id=org_id)
                agent = next((a for a in agents if a['name'] == agent_name), None)
                if agent:
                    print(f"[OK] Found existing agent: {agent['name']} (ID: {agent['id']})")
                else:
                    raise ValueError("Could not find or create agent.")
            else:
                raise

        # 4. List agents
        print("\nListing agents...")
        agents = await client.agents.list(org_id=org_id)
        print(f"[OK] Found {len(agents)} agent(s) in organization {org_id}.")
        for a in agents[:3]:
            print(f"  - {a['name']} (ID: {a['id']})")

        # 5. Send a coordination message (agent to itself)
        print("\nSending a coordination message...")
        receipt = await client.coordination.send_message(
            sender_id=agent['id'],
            recipient_id=agent['id'],
            payload={"action": "self_test", "data": "hello from python"}
        )
        print(f"[OK] Message sent successfully. Receipt: {receipt}")

        # 6. Get economy balance
        print("\nFetching economy balance...")
        balance = await client.economy.get_balance(org_id=org_id)
        print(f"[OK] Current balance: {balance} credits")

        # 7. Get reputation score
        print("\nFetching reputation score...")
        score = await client.reputation.get_agent_score(agent_id=agent['id'], org_id=org_id)
        if score:
            print(f"[OK] Reputation score for {agent['name']}: {score.get('score', 'N/A')}")
        else:
            print(f"- No reputation score found for {agent['name']}.")

    except BrikkError as e:
        print(f"\n[ERROR] An API error occurred: {e.message}")
        if e.response:
            try:
                error_details = await e.response.json()
                print(f"   Details: {error_details}")
            except Exception:
                print(f"   Response: {await e.response.text()}")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")

    print("\n--- Quickstart Finished ---")


if __name__ == "__main__":
    # The SDK is async-first, so we run the main function in an event loop.
    # If you are using the sync client, you can call these methods directly.
    asyncio.run(main())

