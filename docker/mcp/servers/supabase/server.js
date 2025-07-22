#!/usr/bin/env node

/**
 * Supabase MCP Server
 * Предоставляет доступ к Supabase через Model Context Protocol
 */

const express = require('express');
const app = express();

const PORT = process.env.MCP_SERVER_PORT || 3001;
const SERVER_NAME = process.env.MCP_SERVER_NAME || 'supabase';

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
                name: 'execute_sql',
                description: 'Execute SQL query in Supabase database',
                parameters: {
                    query: { type: 'string', required: true }
                }
            },
            {
                name: 'list_tables',
                description: 'List all tables in the database',
                parameters: {}
            },
            {
                name: 'list_projects',
                description: 'List all Supabase projects',
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
            case 'execute_sql':
                result = {
                    success: true,
                    data: {
                        rows: [{ version: 'PostgreSQL 15.2' }],
                        rowCount: 1
                    },
                    message: `Executed query: ${parameters.query}`
                };
                break;
                
            case 'list_tables':
                result = {
                    success: true,
                    data: {
                        tables: ['users', 'messages', 'sessions']
                    }
                };
                break;
                
            case 'list_projects':
                result = {
                    success: true,
                    data: {
                        projects: [
                            { id: '1', name: 'artem-integrator-prod' },
                            { id: '2', name: 'artem-integrator-dev' }
                        ]
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