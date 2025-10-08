#!/usr/bin/env node
/**
 * Brikk Node.js Agent Demo
 * Demonstrates sending an echo job via the coordination protocol.
 */

const BrikkClient = require('./client');

async function main() {
    console.log('🤖 Brikk Node.js Agent Demo');
    console.log('=' .repeat(40));
    
    // Check for dry run mode
    const dryRun = process.argv.includes('--dry-run');
    
    try {
        // Initialize client
        const client = new BrikkClient();
        console.log(`✅ Connected to: ${client.baseUrl}`);
        console.log(`🔑 Agent ID: ${client.apiKey}`);
        
        if (dryRun) {
            console.log('🧪 Dry run mode - skipping network calls');
            console.log('✅ Demo would send echo job successfully');
            return;
        }
        
        // Send echo job to a demo recipient
        const recipient = 'demo-echo-agent';
        const payload = {
            job_type: 'echo',
            message: 'Hello from Node.js agent!',
            data: { test: true, timestamp: 1234567890 }
        };
        
        console.log(`\n📤 Sending echo job to: ${recipient}`);
        console.log(`📦 Payload:`, payload);
        
        // Send the message
        const response = await client.send(recipient, payload);
        
        console.log(`\n✅ Response received:`);
        console.log(`📨 Status: ${response.status || 'unknown'}`);
        console.log(`🆔 Message ID: ${response.message_id || 'N/A'}`);
        
        // Poll for any incoming messages
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
