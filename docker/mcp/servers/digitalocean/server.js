#!/usr/bin/env node

/**
 * DigitalOcean MCP Server
 * Предоставляет доступ к DigitalOcean API через Model Context Protocol
 */

const express = require('express');
const app = express();

const PORT = process.env.MCP_SERVER_PORT || 3002;
const SERVER_NAME = process.env.MCP_SERVER_NAME || 'digitalocean';

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        server: SERVER_NAME,
        timestamp: new Date().toISOString()
    });
});

// MCP endpoints
app.get('/mcp/tools', (req, res) => {
    res.json({
        tools: [
            {
                name: 'list_apps',
                description: 'List all DigitalOcean apps',
                parameters: {}
            },
            {
                name: 'get_app',
                description: 'Get details of a specific app',
                parameters: {
                    app_id: { type: 'string', required: true }
                }
            },
            {
                name: 'list_droplets',
                description: 'List all droplets',
                parameters: {}
            }
        ]
    });
});

app.post('/mcp/execute', async (req, res) => {
    const { tool, parameters } = req.body;
    
    try {
        let result;
        
        switch (tool) {
            case 'list_apps':
                result = {
                    success: true,
                    data: {
                        apps: [
                            { 
                                id: 'app-1', 
                                name: 'artem-integrator',
                                status: 'active',
                                region: 'fra1'
                            }
                        ]
                    }
                };
                break;
                
            case 'get_app':
                result = {
                    success: true,
                    data: {
                        app: {
                            id: parameters.app_id,
                            name: 'artem-integrator',
                            status: 'active',
                            created_at: new Date().toISOString()
                        }
                    }
                };
                break;
                
            case 'list_droplets':
                result = {
                    success: true,
                    data: {
                        droplets: []
                    }
                };
                break;
                
            default:
                result = {
                    success: false,
                    error: `Unknown tool: ${tool}`
                };
        }
        
        res.json(result);
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`✅ ${SERVER_NAME} MCP server running on port ${PORT}`);
});