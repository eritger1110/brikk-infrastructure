#!/usr/bin/env node
/**
 * Brikk Node.js Agent Client
 * Simple SDK for communicating with the Brikk coordination protocol.
 */

const crypto = require('crypto');
const https = require('https');
const http = require('http');
const { URL } = require('url');

class BrikkClient {
    /**
     * Simple client for Brikk coordination protocol with HMAC authentication.
     */
    constructor(baseUrl = null, apiKey = null, secret = null) {
        this.baseUrl = baseUrl || process.env.BRIKK_BASE_URL || 'http://localhost:5000';
        this.apiKey = apiKey || process.env.BRIKK_API_KEY;
        this.secret = secret || process.env.BRIKK_SECRET;
        
        if (!this.apiKey || !this.secret) {
            throw new Error('BRIKK_API_KEY and BRIKK_SECRET environment variables required');
        }
    }
    
    /**
     * Generate HMAC signature for request authentication.
     */
    _signRequest(method, path, body = '') {
        const timestamp = Math.floor(Date.now() / 1000).toString();
        const message = `${method}\n${path}\n${body}\n${timestamp}`;
        const signature = crypto
            .createHmac('sha256', this.secret)
            .update(message)
            .digest('hex');
        return `${timestamp}:${signature}`;
    }
    
    /**
     * Send a coordination message to another agent.
     */
    async send(to, payload) {
        const envelope = {
            version: '1.0',
            sender: this.apiKey,
            recipient: to,
            payload: payload,
            timestamp: Math.floor(Date.now() / 1000)
        };
        
        const body = JSON.stringify(envelope);
        const path = '/api/v1/coordination';
        const authHeader = this._signRequest('POST', path, body);
        
        const url = new URL(this.baseUrl + path);
        const isHttps = url.protocol === 'https:';
        const client = isHttps ? https : http;
        
        return new Promise((resolve, reject) => {
            const options = {
                hostname: url.hostname,
                port: url.port || (isHttps ? 443 : 80),
                path: path,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(body),
                    'Authorization': `HMAC ${this.apiKey}:${authHeader}`
                }
            };
            
            const req = client.request(options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    if (res.statusCode >= 200 && res.statusCode < 300) {
                        resolve(JSON.parse(data));
                    } else {
                        reject(new Error(`HTTP ${res.statusCode}: ${data}`));
                    }
                });
            });
            
            req.on('error', reject);
            req.write(body);
            req.end();
        });
    }
    
    /**
     * Poll for incoming messages (mock implementation).
     */
    async poll() {
        return { status: 'no_messages', messages: [] };
    }
}

module.exports = BrikkClient;
