/**
 * Brikk Node.js SDK Quickstart Example
 *
 * This script demonstrates the core functionality of the Brikk Node.js SDK.
 *
 * To run this example:
 * 1. Install dependencies: `pnpm install`
 * 2. Build the SDK: `pnpm --filter @brikk/sdk build`
 * 3. Set environment variables:
 *    - `BRIKK_BASE_URL`: Your Brikk API base URL (e.g., http://localhost:8000)
 *    - `BRIKK_API_KEY`: Your API key
 *    - `BRIKK_SIGNING_SECRET`: Your signing secret for HMAC auth
 *    - `BRIKK_ORG_ID`: Your organization ID
 * 4. Run the script: `pnpm tsx examples/sdk/node_quickstart.ts`
 */

import { BrikkClient, BrikkError } from '@brikk/sdk';

async function main() {
  console.log('--- Brikk Node.js SDK Quickstart ---');

  // 1. Initialize the client from environment variables
  let client: BrikkClient;
  try {
    client = new BrikkClient();
    console.log(`✅ Client initialized for base URL: ${client.baseUrl}`);
  } catch (e) {
    console.error(`❌ Failed to initialize client: ${e}`);
    return;
  }

  const orgId = client.orgId;
  if (!orgId) {
    console.error('❌ BRIKK_ORG_ID environment variable not set. Aborting.');
    return;
  }

  try {
    // 2. Check API health
    console.log('\nPinging health check endpoint...');
    const health = await client.health.ping();
    console.log(`✅ Health status: ${health.status}`);

    // 3. Create a new agent (or use an existing one)
    console.log('\nCreating or getting an agent...');
    const agentName = 'My Node.js SDK Agent';
    let agent;
    try {
      agent = await client.agents.create(agentName, orgId);
      console.log(`✅ Created new agent: ${agent.name} (ID: ${agent.id})`);
    } catch (e) {
      if (e instanceof BrikkError && e.statusCode === 409) {
        const agents = await client.agents.list(orgId);
        agent = agents.find(a => a.name === agentName);
        if (agent) {
          console.log(`✅ Found existing agent: ${agent.name} (ID: ${agent.id})`);
        } else {
          throw new Error('Could not find or create agent.');
        }
      } else {
        throw e;
      }
    }

    // 4. List agents
    console.log('\nListing agents...');
    const agents = await client.agents.list(orgId);
    console.log(`✅ Found ${agents.length} agent(s) in organization ${orgId}.`);
    agents.slice(0, 3).forEach(a => {
      console.log(`  - ${a.name} (ID: ${a.id})`);
    });

    // 5. Send a coordination message (agent to itself)
    console.log('\nSending a coordination message...');
    const receipt = await client.coordination.sendMessage(
      agent!.id,
      agent!.id,
      { action: 'self_test', data: 'hello from node' }
    );
    console.log('✅ Message sent successfully. Receipt:', receipt);

    // 6. Get economy balance
    console.log('\nFetching economy balance...');
    const balance = await client.economy.getBalance(orgId);
    console.log(`✅ Current balance: ${balance} credits`);

    // 7. Get reputation score
    console.log('\nFetching reputation score...');
    const score = await client.reputation.getAgentScore(agent!.id, orgId);
    if (score) {
      console.log(`✅ Reputation score for ${agent!.name}: ${score.score ?? 'N/A'}`);
    } else {
      console.log(`- No reputation score found for ${agent!.name}.`);
    }

  } catch (e) {
    if (e instanceof BrikkError) {
      console.error(`\n❌ An API error occurred: ${e.message}`);
      if (e.response) {
        try {
          const errorDetails = await e.response.json();
          console.error('   Details:', errorDetails);
        } catch {
          console.error('   Response:', await e.response.text());
        }
      }
    } else {
      console.error(`\n❌ An unexpected error occurred: ${e}`);
    }
  }

  console.log('\n--- Quickstart Finished ---');
}

main().catch(console.error);

