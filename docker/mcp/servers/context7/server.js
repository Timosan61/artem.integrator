#!/usr/bin/env node

/**
 * Context7 MCP Server
 * Предоставляет доступ к документации через Model Context Protocol
 */

const express = require('express');
const app = express();

const PORT = process.env.MCP_SERVER_PORT || 3003;
const SERVER_NAME = process.env.MCP_SERVER_NAME || 'context7';

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
                name: 'search_docs',
                description: 'Search documentation for a library',
                parameters: {
                    library: { type: 'string', required: true },
                    query: { type: 'string', required: true }
                }
            },
            {
                name: 'resolve_library',
                description: 'Resolve library name to ID',
                parameters: {
                    library_name: { type: 'string', required: true }
                }
            }
        ]
    });
});

app.post('/mcp/execute', async (req, res) => {
    const { tool, parameters } = req.body;
    
    try {
        let result;
        
        switch (tool) {
            case 'search_docs':
                result = {
                    success: true,
                    data: {
                        results: [
                            {
                                title: `${parameters.library} - ${parameters.query}`,
                                content: `Documentation for ${parameters.query} in ${parameters.library}`,
                                url: `https://docs.example.com/${parameters.library}/${parameters.query}`
                            }
                        ]
                    }
                };
                break;
                
            case 'resolve_library':
                result = {
                    success: true,
                    data: {
                        library_id: `/org/${parameters.library_name}`,
                        name: parameters.library_name,
                        description: `Library ${parameters.library_name}`
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