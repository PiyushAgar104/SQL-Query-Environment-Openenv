---
title: SQL Query Env
emoji: 🗃️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
---

# 🗃️ SQL Query Environment

**An OpenEnv environment for teaching AI agents to write correct SQL queries.**

[![OpenEnv Compatible](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/downloads/)
[![License: BSD-3](https://img.shields.io/badge/License-BSD--3-yellow.svg)](LICENSE)

## Overview

The SQL Query Environment is a real-world OpenEnv-compliant environment that simulates a **Text-to-SQL** task. An AI agent is given a natural-language question and a database schema, and must write correct SQL queries to retrieve the requested data from an e-commerce database.

This environment is designed for **reinforcement learning training** of language model agents, providing:
- **Meaningful partial-credit scoring** (0.0 – 1.0) with multi-signal rewards
- **3 difficulty levels** (easy → medium → hard) with agent-graded tasks
- **Iterative refinement** — agents get feedback and can retry up to 5 times
- **Zero external dependencies** — pure Python + SQLite, runs anywhere

## Quick Start

### Install

```bash
pip install openenv-core[core]
pip install git+https://huggingface.co/spaces/YOUR_USERNAME/sql_query_env
```

### Use the environment

```python
from sql_query_env import SQLQueryEnv

with SQLQueryEnv(base_url="http://localhost:8000").sync() as env:
    # Reset to get a task
    result = env.reset()
    
    # Get the database schema
    schema = env.call_tool("get_schema")
    print(schema)
    
    # Submit a SQL query
    result = env.call_tool(
        "submit_query",
        sql="SELECT name, email FROM customers WHERE city = 'Mumbai' ORDER BY signup_date"
    )
    print(result)  # Score, feedback, query results
```

## Environment Details

### Database Schema

The environment uses an **e-commerce database** with 4 tables:

```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### Action Space (MCP Tools)

| Tool | Arguments | Description |
|------|-----------|-------------|
| `submit_query` | `sql: str` | Execute a SQL query and get graded results |
| `get_schema` | *(none)* | Return the database schema as DDL |
| `get_hint` | *(none)* | Get a hint for the current task (costs -0.1 reward) |

### Observation Space

On `reset()`:
| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Unique task identifier |
| `difficulty` | `str` | "easy", "medium", or "hard" |
| `task_description` | `str` | Natural language question |
| `schema` | `str` | Database DDL |
| `max_steps` | `int` | Maximum attempts allowed |

On `submit_query`:
| Field | Type | Description |
|-------|------|-------------|
| `score` | `float` | Score from 0.0 to 1.0 |
| `feedback` | `str` | Human-readable grading feedback |
| `columns` | `list[str]` | Output column names |
| `rows` | `list[list]` | Query result rows (up to 20) |
| `total_rows` | `int` | Total row count |
| `error` | `str or null` | Error message if query failed |

## Tasks

### Task 1: Easy — Customer Lookup
> *"List all customers who are from the city 'Mumbai'. Return their name, email, and signup_date."*

**SQL Concepts**: `SELECT`, `WHERE`, `ORDER BY`

### Task 2: Medium — Top Customers by Spending
> *"Find the top 3 customers who have spent the most money overall."*

**SQL Concepts**: `JOIN`, `GROUP BY`, `SUM()`, `ORDER BY DESC`, `LIMIT`

### Task 3: Hard — Best Product per Category
> *"For each product category, find the single product that has generated the highest total revenue."*

**SQL Concepts**: Subquery/CTE, multi-table `JOIN`, `GROUP BY`, `HAVING`, `SUM()`

## Scoring

Scores range from **0.0 to 1.0** using weighted partial credit:

```
Score = 0.2 * execution_score + 0.3 * column_score + 0.5 * data_score
```

| Component | Weight | What it measures |
|-----------|--------|------------------|
| `execution_score` | 0.2 | Query runs without errors |
| `column_score` | 0.3 | Output columns match expected (Jaccard similarity) |
| `data_score` | 0.5 | Output data matches expected (F1-style matching) |

**Hint penalty**: Each `get_hint` call subtracts 0.1 from the final score.

## Setup & Development

### Run Locally

```bash
# Clone and install
cd sql_query_env
pip install -e .

# Start the server
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Open API docs
open http://localhost:8000/docs
```

### Run with Docker

```bash
# Build the image
docker build -t sql-query-env .

# Run the container
docker run -p 8000:8000 sql-query-env

# Test health
curl http://localhost:8000/health
```

### Run Baseline Inference

```bash
# Rule-based baseline (no API key needed)
python inference.py --strategy rule-based --url http://localhost:8000

# LLM baseline (requires OPENAI_API_KEY)
export OPENAI_API_KEY=your-key-here
python inference.py --strategy llm --url http://localhost:8000

# Specific task only
python inference.py --strategy llm --tasks task_easy_001
```

### Expected Baseline Scores

| Strategy | Easy | Medium | Hard | Average |
|----------|------|--------|------|---------|
| Rule-based | ~0.70 | ~0.50 | ~0.20 | ~0.47 |
| GPT-4o-mini | ~1.00 | ~0.90 | ~0.70 | ~0.87 |

## Deploy to Hugging Face Spaces

```bash
# Install OpenEnv CLI
pip install openenv-core

# Push to HF Spaces
cd sql_query_env
openenv push --repo-id YOUR_USERNAME/sql_query_env
```

## API Reference

### HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reset` | Reset environment, optionally specify `task_id` or `difficulty` |
| `POST` | `/step` | Execute an action (MCP CallToolAction) |
| `GET` | `/state` | Get current episode state |
| `GET` | `/health` | Health check |
| `GET` | `/schema` | JSON schema for action/observation types |
| `GET` | `/docs` | Swagger API documentation |
| `WS` | `/ws` | WebSocket connection for persistent sessions |

### Reset Parameters

```json
{
    "seed": 42,
    "task_id": "task_easy_001",
    "difficulty": "easy"
}
```

### Step Action (MCP CallToolAction)

```json
{
    "action": {
        "type": "call_tool",
        "tool_name": "submit_query",
        "arguments": {
            "sql": "SELECT name FROM customers WHERE city = 'Mumbai'"
        }
    }
}
```

## License

BSD-3-Clause — same as OpenEnv.
