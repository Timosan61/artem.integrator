"""
MCP Mock Server для локального тестирования

Эмулирует ответы MCP серверов:
- Supabase
- DigitalOcean  
- Context7
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Mock Server", version="1.0.0")


# Модели запросов/ответов
class MCPRequest(BaseModel):
    tool: str
    parameters: Dict[str, Any]


class MCPResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Mock данные
MOCK_DATA = {
    # Supabase
    "mcp__supabase__list_projects": {
        "projects": [
            {
                "id": "proj_test_123",
                "name": "Test Project",
                "status": "active",
                "created_at": "2024-01-15T10:00:00Z",
                "region": "us-east-1"
            },
            {
                "id": "proj_demo_456", 
                "name": "Demo Project",
                "status": "paused",
                "created_at": "2024-01-10T15:30:00Z",
                "region": "eu-west-1"
            }
        ]
    },
    
    "mcp__supabase__execute_sql": {
        "rows": [
            {"version": "PostgreSQL 15.1"},
            {"current_timestamp": datetime.now().isoformat()}
        ],
        "affected_rows": 0
    },
    
    "mcp__supabase__list_tables": {
        "tables": [
            {"schema": "public", "name": "users", "type": "table"},
            {"schema": "public", "name": "messages", "type": "table"},
            {"schema": "public", "name": "sessions", "type": "table"}
        ]
    },
    
    # DigitalOcean
    "mcp__digitalocean__list_apps": {
        "apps": [
            {
                "id": "app_artem_bot",
                "name": "artem-bot",
                "status": "active",
                "live_url": "https://artem-bot.digitaloceanapp.com",
                "created_at": "2024-01-20T12:00:00Z"
            },
            {
                "id": "app_test_api",
                "name": "test-api",
                "status": "deploying",
                "created_at": "2024-01-21T08:00:00Z"
            }
        ]
    },
    
    "mcp__digitalocean__get_deployment_logs_url": {
        "url": "https://mock-logs.digitalocean.com/logs/test-deployment"
    },
    
    "mcp__digitalocean__download_logs": {
        "logs": """
2024-01-21 10:00:00 [INFO] Application starting...
2024-01-21 10:00:01 [INFO] Connected to database
2024-01-21 10:00:02 [INFO] MCP services initialized
2024-01-21 10:00:03 [INFO] Webhook server started on port 8000
2024-01-21 10:00:05 [INFO] Ready to receive messages
        """.strip()
    },
    
    # Context7
    "mcp__context7__resolve-library-id": {
        "library_id": "/npm/react",
        "name": "React",
        "version": "18.2.0"
    },
    
    "mcp__context7__get-library-docs": {
        "documentation": """
# React Hooks Documentation

Hooks are a new addition in React 16.8. They let you use state and other React features without writing a class.

## useState

```javascript
const [state, setState] = useState(initialState);
```

Returns a stateful value, and a function to update it.

## useEffect

```javascript
useEffect(() => {
  // Side effect logic
  return () => {
    // Cleanup
  };
}, [dependencies]);
```

Accepts a function that contains imperative, possibly effectful code.
        """.strip()
    }
}


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "MCP Mock Server",
        "status": "running",
        "available_tools": list(MOCK_DATA.keys())
    }


@app.post("/mcp/execute")
async def execute_mcp_tool(request: MCPRequest):
    """Выполняет mock MCP tool"""
    logger.info(f"Executing MCP tool: {request.tool}")
    logger.debug(f"Parameters: {request.parameters}")
    
    # Проверяем, есть ли mock данные для этого tool
    if request.tool in MOCK_DATA:
        # Специальная обработка для некоторых tools
        if request.tool == "mcp__supabase__execute_sql":
            # Можем добавить логику в зависимости от SQL запроса
            query = request.parameters.get("query", "").lower()
            if "select version()" in query:
                return MCPResponse(
                    success=True,
                    data={"rows": [{"version": "PostgreSQL 15.1"}]}
                )
            elif "select" in query:
                return MCPResponse(
                    success=True,
                    data=MOCK_DATA[request.tool]
                )
        
        # Возвращаем mock данные
        return MCPResponse(
            success=True,
            data=MOCK_DATA[request.tool]
        )
    else:
        # Tool не найден
        logger.warning(f"Unknown MCP tool: {request.tool}")
        return MCPResponse(
            success=False,
            error=f"Unknown MCP tool: {request.tool}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# Endpoints для отдельных сервисов
@app.get("/supabase/status")
async def supabase_status():
    """Статус Supabase mock"""
    return {
        "service": "Supabase Mock",
        "status": "active",
        "available_functions": [
            "list_projects",
            "execute_sql",
            "list_tables",
            "create_project"
        ]
    }


@app.get("/digitalocean/status")
async def digitalocean_status():
    """Статус DigitalOcean mock"""
    return {
        "service": "DigitalOcean Mock",
        "status": "active",
        "available_functions": [
            "list_apps",
            "get_app_logs",
            "create_deployment",
            "get_deployment_status"
        ]
    }


@app.get("/context7/status")
async def context7_status():
    """Статус Context7 mock"""
    return {
        "service": "Context7 Mock",
        "status": "active",
        "available_functions": [
            "search_docs",
            "get_library_docs",
            "get_code_examples"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, reload=True)