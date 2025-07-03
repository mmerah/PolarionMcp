#!/usr/bin/env node
/**
 * MCP HTTP Client
 * Production-ready HTTP client for MCP (Model Context Protocol) servers
 * 
 * This script bridges stdio-based MCP clients (like Cline) to HTTP-based MCP servers.
 * It handles JSON-RPC message translation, session management, and SSL/TLS connections.
 * 
 * @version 1.0.0
 * @license MIT
 */

'use strict';

const readline = require('readline');
const https = require('https');
const http = require('http');
const { URL } = require('url');

// Configuration
const CONFIG = {
  REQUEST_TIMEOUT: 30000, // 30 seconds
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000, // 1 second
};

// Get server URL from command line arguments
const serverUrl = process.argv[2];
if (!serverUrl) {
  console.error('Usage: node mcp-http-client.js <server-url>');
  console.error('Example: node mcp-http-client.js https://localhost:8443/mcp/');
  process.exit(1);
}

// Validate and parse URL
let url;
try {
  url = new URL(serverUrl);
} catch (error) {
  console.error(`Invalid URL: ${serverUrl}`);
  process.exit(1);
}

const isHttps = url.protocol === 'https:';
const client = isHttps ? https : http;

// Handle SSL/TLS settings for development
if (process.env.NODE_TLS_REJECT_UNAUTHORIZED === '0') {
  if (process.env.NODE_ENV === 'production') {
    console.warn('WARNING: SSL certificate verification is disabled in production mode');
  }
  process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 0;
}

// Create readline interface for stdio communication
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Session management
let sessionId = null;
let requestCounter = 0;

// Statistics
const stats = {
  requestsSent: 0,
  responsesReceived: 0,
  errorsEncountered: 0,
  startTime: Date.now()
};

/**
 * Log debug information (only in development)
 * @param {string} message - Debug message
 * @param {Object} data - Optional data to log
 */
function debugLog(message, data = null) {
  if (process.env.NODE_ENV === 'development') {
    console.error(`[MCP-CLIENT] ${message}`, data ? JSON.stringify(data) : '');
  }
}

/**
 * Create a JSON-RPC error response
 * @param {string|number} id - Request ID
 * @param {number} code - Error code
 * @param {string} message - Error message
 * @returns {Object} JSON-RPC error response
 */
function createErrorResponse(id, code, message) {
  return {
    jsonrpc: '2.0',
    id,
    error: {
      code,
      message
    }
  };
}

/**
 * Make HTTP request with retry logic
 * @param {Object} request - JSON-RPC request
 * @param {number} retryCount - Current retry attempt
 * @returns {Promise} Promise that resolves with response
 */
function makeRequest(request, retryCount = 0) {
  return new Promise((resolve, reject) => {
    const requestData = JSON.stringify(request);
    
    const options = {
      hostname: url.hostname,
      port: url.port || (isHttps ? 443 : 80),
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(requestData),
        'User-Agent': 'MCP-HTTP-Client/1.0.0'
      },
      timeout: CONFIG.REQUEST_TIMEOUT
    };
    
    // Add session ID header if available
    if (sessionId) {
      options.headers['Mcp-Session-Id'] = sessionId;
    }
    
    // Handle self-signed certificates in development
    if (isHttps && process.env.NODE_TLS_REJECT_UNAUTHORIZED === '0') {
      options.rejectUnauthorized = false;
    }
    
    debugLog(`Making request (attempt ${retryCount + 1})`, { method: request.method, id: request.id });
    
    const req = client.request(options, (res) => {
      let data = '';
      
      // Extract session ID from response headers
      if (res.headers['mcp-session-id']) {
        sessionId = res.headers['mcp-session-id'];
        debugLog('Session ID updated', { sessionId });
      }
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        stats.responsesReceived++;
        
        try {
          const response = JSON.parse(data);
          debugLog('Response received', { id: response.id, hasError: !!response.error });
          resolve(response);
        } catch (parseError) {
          const errorResponse = createErrorResponse(
            request.id,
            -32603,
            `Failed to parse server response: ${parseError.message}`
          );
          resolve(errorResponse);
        }
      });
    });
    
    req.on('error', (error) => {
      stats.errorsEncountered++;
      debugLog('Request error', { error: error.message, retryCount });
      
      // Retry logic for network errors
      if (retryCount < CONFIG.MAX_RETRIES && isRetryableError(error)) {
        setTimeout(() => {
          makeRequest(request, retryCount + 1)
            .then(resolve)
            .catch(reject);
        }, CONFIG.RETRY_DELAY * (retryCount + 1));
      } else {
        const errorResponse = createErrorResponse(
          request.id,
          -32603,
          `Request failed: ${error.message}`
        );
        resolve(errorResponse);
      }
    });
    
    req.on('timeout', () => {
      req.destroy();
      const errorResponse = createErrorResponse(
        request.id,
        -32603,
        'Request timeout'
      );
      resolve(errorResponse);
    });
    
    // Send the request
    req.write(requestData);
    req.end();
  });
}

/**
 * Check if error is retryable
 * @param {Error} error - The error to check
 * @returns {boolean} True if error is retryable
 */
function isRetryableError(error) {
  const retryableCodes = ['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'ENOTFOUND'];
  return retryableCodes.includes(error.code);
}

// Handle incoming JSON-RPC messages from stdin
rl.on('line', async (line) => {
  try {
    const request = JSON.parse(line.trim());
    
    // Validate JSON-RPC request
    if (!request.jsonrpc || request.jsonrpc !== '2.0') {
      const errorResponse = createErrorResponse(
        request.id,
        -32600,
        'Invalid JSON-RPC version'
      );
      console.log(JSON.stringify(errorResponse));
      return;
    }
    
    if (!request.method) {
      const errorResponse = createErrorResponse(
        request.id,
        -32600,
        'Missing method in request'
      );
      console.log(JSON.stringify(errorResponse));
      return;
    }
    
    // Assign ID if not present
    if (request.id === undefined) {
      request.id = ++requestCounter;
    }
    
    stats.requestsSent++;
    debugLog('Processing request', { method: request.method, id: request.id });
    
    // Make HTTP request to the MCP server
    const response = await makeRequest(request);
    
    // Send response back to stdout
    console.log(JSON.stringify(response));
    
  } catch (parseError) {
    stats.errorsEncountered++;
    const errorResponse = createErrorResponse(
      null,
      -32700,
      `Parse error: ${parseError.message}`
    );
    console.log(JSON.stringify(errorResponse));
  }
});

// Handle process termination gracefully
function gracefulShutdown(signal) {
  const uptime = Date.now() - stats.startTime;
  debugLog(`Shutting down on ${signal}`, {
    uptime: `${uptime}ms`,
    requestsSent: stats.requestsSent,
    responsesReceived: stats.responsesReceived,
    errorsEncountered: stats.errorsEncountered
  });
  
  rl.close();
  process.exit(0);
}

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  stats.errorsEncountered++;
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  stats.errorsEncountered++;
  process.exit(1);
});

// Initialize
debugLog('MCP HTTP Client started', { serverUrl, isHttps });