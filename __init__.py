"""
SQL Query Environment - An OpenEnv environment for teaching AI agents to write SQL.

This environment presents natural-language questions about an e-commerce database
and challenges agents to write correct SQL queries. Scoring uses partial credit
(0.0 - 1.0) based on schema match, column correctness, and data accuracy.

MCP Tools available:
- submit_query(sql): Execute and grade a SQL query
- get_schema(): Return the database schema DDL
- get_hint(): Get a hint for the current task (costs reward penalty)

Example:
    >>> from sql_query_env import SQLQueryEnv
    >>>
    >>> with SQLQueryEnv(base_url="http://localhost:8000") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("submit_query", sql="SELECT * FROM customers")
"""

from openenv.core.env_server.mcp_types import CallToolAction, ListToolsAction

from .client import SQLQueryEnv

__all__ = ["SQLQueryEnv", "CallToolAction", "ListToolsAction"]
