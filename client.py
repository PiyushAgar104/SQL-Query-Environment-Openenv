"""
SQL Query Environment Client.

Provides the client for connecting to a SQL Query Environment server.
SQLQueryEnv extends MCPToolClient to provide tool-calling style interactions.

Example:
    >>> with SQLQueryEnv(base_url="http://localhost:8000") as env:
    ...     env.reset()
    ...
    ...     # Discover tools
    ...     tools = env.list_tools()
    ...     print([t.name for t in tools])
    ...
    ...     # Submit a SQL query
    ...     result = env.call_tool("submit_query", sql="SELECT * FROM customers WHERE city = 'Mumbai'")
    ...     print(result)
    ...
    ...     # Get the database schema
    ...     schema = env.call_tool("get_schema")
    ...     print(schema)
"""

from openenv.core.mcp_client import MCPToolClient


class SQLQueryEnv(MCPToolClient):
    """
    Client for the SQL Query Environment.

    This client provides a simple interface for interacting with the SQL Query
    Environment via MCP tools. It inherits all functionality from MCPToolClient:
    - `list_tools()`: Discover available tools
    - `call_tool(name, **kwargs)`: Call a tool by name
    - `reset(**kwargs)`: Reset the environment
    - `step(action)`: Execute an action (for advanced use)

    Available MCP tools:
    - `submit_query(sql)`: Execute a SQL query and get graded results
    - `get_schema()`: Get the database schema as DDL
    - `get_hint()`: Get a hint for the current task (penalty: -0.1 reward)

    Example:
        >>> with SQLQueryEnv(base_url="http://localhost:8000") as env:
        ...     env.reset()
        ...     schema = env.call_tool("get_schema")
        ...     result = env.call_tool("submit_query", sql="SELECT name FROM customers")
        ...     print(result)

    Example with Docker:
        >>> env = SQLQueryEnv.from_docker_image("sql-query-env:latest")
        >>> try:
        ...     env.reset()
        ...     tools = env.list_tools()
        ...     result = env.call_tool("submit_query", sql="SELECT 1")
        ... finally:
        ...     env.close()
    """

    pass  # MCPToolClient provides all needed functionality
