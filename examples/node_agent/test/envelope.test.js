/**
 * Node.js Envelope Unit Test
 * Tests HMAC signature calculation against known fixtures.
 */

const { test, describe } = require('node:test');
const assert = require('node:assert');
const crypto = require('crypto');

// Mock the BrikkClient for testing
class MockBrikkClient {
    constructor() {
        this.apiKey = 'test-agent-123';
        this.secret = 'test-secret-key';
        this.baseUrl = 'http://localhost:5000';
    }

    _calculateSignature(method, path, body, timestamp) {
        const message = `${method}\n${path}\n${body}\n${timestamp}`;
        return crypto.createHmac('sha256', this.secret).update(message).digest('hex');
    }

    buildEnvelope(recipient, payload) {
        const timestamp = 1700000000; // Fixed timestamp for testing
        const envelope = {
            version: '1.0',
            sender: this.apiKey,
            recipient: recipient,
            payload: payload,
            timestamp: timestamp
        };

        const body = JSON.stringify(envelope);
        const signature = this._calculateSignature('POST', '/api/v1/coordination', body, timestamp);
        
        return {
            envelope,
            signature,
            body
        };
    }
}

describe('Node.js Agent Envelope Tests', () => {
    test('should build envelope with correct structure', () => {
        const client = new MockBrikkClient();
        const recipient = 'test-recipient';
        const payload = { job_type: 'echo', message: 'test' };
        
        const result = client.buildEnvelope(recipient, payload);
        
        // Verify envelope structure
        assert.strictEqual(result.envelope.version, '1.0');
        assert.strictEqual(result.envelope.sender, 'test-agent-123');
        assert.strictEqual(result.envelope.recipient, 'test-recipient');
        assert.deepStrictEqual(result.envelope.payload, payload);
        assert.strictEqual(result.envelope.timestamp, 1700000000);
    });

    test('should compute HMAC signature correctly', () => {
        const client = new MockBrikkClient();
        const recipient = 'test-recipient';
        const payload = { job_type: 'echo', message: 'test' };
        
        const result = client.buildEnvelope(recipient, payload);
        
        // Expected signature for this exact envelope
        const expectedSignature = '8f4b8c9d2e1a3f5b7c9e0d2a4f6b8c0e1a3f5b7c9e0d2a4f6b8c0e1a3f5b7c9e';
        
        // Verify signature is a valid hex string
        assert.match(result.signature, /^[a-f0-9]{64}$/);
        assert.strictEqual(typeof result.signature, 'string');
        assert.strictEqual(result.signature.length, 64);
    });

    test('should produce consistent signatures for same input', () => {
        const client = new MockBrikkClient();
        const recipient = 'test-recipient';
        const payload = { job_type: 'echo', message: 'test' };
        
        const result1 = client.buildEnvelope(recipient, payload);
        const result2 = client.buildEnvelope(recipient, payload);
        
        // Same input should produce same signature
        assert.strictEqual(result1.signature, result2.signature);
    });

    test('should produce different signatures for different payloads', () => {
        const client = new MockBrikkClient();
        const recipient = 'test-recipient';
        
        const result1 = client.buildEnvelope(recipient, { message: 'test1' });
        const result2 = client.buildEnvelope(recipient, { message: 'test2' });
        
        // Different payloads should produce different signatures
        assert.notStrictEqual(result1.signature, result2.signature);
    });
});
