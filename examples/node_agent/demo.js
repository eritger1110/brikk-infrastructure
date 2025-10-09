#!/usr/bin/env node
/**
 * Brikk Node.js Agent Demo
 * Demonstrates sending an echo job via the coordination protocol.
 */

const BrikkClient = require('./client');

async function main() {
  console.log('🤖 Brikk Node.js Agent Demo');
  console.log('='.repeat(40));

  // Dry-run if --dry-run flag or CI wants no network
  const dryRun = process.argv.includes('--dry-run') || process.env.NO_NETWORK === '1';

  try {
    if (dryRun) {
      // Safe dummy defaults so the script runs offline
      process.env.BRIKK_API_KEY = process.env.BRIKK_API_KEY || 'demo-node-agent';
      process.env.BRIKK_SECRET  = process.env.BRIKK_SECRET  || 'demo-secret-key';
      process.env.BRIKK_BASE_URL = process.env.BRIKK_BASE_URL || 'http://localhost:5000';
    }

    // Initialize client
    const client = new BrikkClient();
    console.log(`✅ Connected to: ${client.baseUrl}`);
    console.log(`🔑 Agent ID: ${client.apiKey}`);

    if (dryRun) {
      console.log('🧪 Dry run mode - building envelope without network calls');

      const recipient = 'demo-echo-agent';
      const payload = {
        job_type: 'echo',
        message: 'Hello from Node.js agent!',
        data: { test: true, timestamp: 1234567890 }
      };

      const envelope = {
        version: '1.0',
        sender: client.apiKey,
        recipient,
        payload,
        timestamp: Math.floor(Date.now() / 1000)
      };

      console.log('\n📦 Coordination envelope:');
      console.log(JSON.stringify(envelope, null, 2));
      console.log('✅ Demo envelope built successfully');
      return;
    }

    // Online path: send echo job
    const recipient = 'demo-echo-agent';
    const payload = {
      job_type: 'echo',
      message: 'Hello from Node.js agent!',
      data: { test: true, timestamp: 1234567890 }
    };

    console.log(`\n📤 Sending echo job to: ${recipient}`);
    console.log('📦 Payload:', payload);

    const response = await client.send(recipient, payload);

    console.log('\n✅ Response received:');
    console.log(`📨 Status: ${response.status || 'unknown'}`);
    console.log(`🆔 Message ID: ${response.message_id || 'N/A'}`);

    const messages = await client.poll();
    console.log(`\n📬 Polling result: ${messages.status}`);
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
