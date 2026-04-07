#!/usr/bin/env python3
"""
Baseline Inference Script for the SQL Query Environment.

Provides two inference strategies:
1. Rule-based (no API key): Pattern matching to construct basic SQL
2. LLM-based (requires OPENAI_API_KEY): Uses GPT to generate SQL

Usage:
    # Rule-based baseline (no API key needed)
    python inference.py --strategy rule-based --url http://localhost:8000

    # LLM-based baseline (requires OPENAI_API_KEY env var)
    python inference.py --strategy llm --url http://localhost:8000

    # Run all tasks with a specific strategy
    python inference.py --strategy llm --tasks all --url http://localhost:8000
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

# We use requests directly to avoid requiring openenv client install
import requests


# ─── HTTP Helpers ─────────────────────────────────────────────────────────────

class SQLQueryEnvHTTPClient:
    """Simple HTTP client for the SQL Query Environment."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health(self) -> dict:
        """Check server health."""
        resp = self.session.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def reset(self, task_id: Optional[str] = None, difficulty: Optional[str] = None, seed: int = 42) -> dict:
        """Reset the environment."""
        payload = {"seed": seed}
        if task_id:
            payload["task_id"] = task_id
        if difficulty:
            payload["difficulty"] = difficulty
        resp = self.session.post(f"{self.base_url}/reset", json=payload)
        resp.raise_for_status()
        return resp.json()

    def step(self, action: dict) -> dict:
        """Execute a step."""
        payload = {"action": action}
        resp = self.session.post(f"{self.base_url}/step", json=payload)
        resp.raise_for_status()
        return resp.json()

    def state(self) -> dict:
        """Get current state."""
        resp = self.session.get(f"{self.base_url}/state")
        resp.raise_for_status()
        return resp.json()


# ─── Rule-Based Strategy ─────────────────────────────────────────────────────

def rule_based_inference(task_description: str, schema: str) -> str:
    """
    Generate SQL using simple rule-based pattern matching.

    This is a baseline that demonstrates basic keyword extraction
    without any ML/LLM. Scores will be modest but non-zero.
    """
    desc_lower = task_description.lower()

    # Easy: List customers from a city
    if "customers" in desc_lower and ("city" in desc_lower or "from" in desc_lower):
        # Extract city name (look for quoted strings)
        city_match = re.search(r"'([^']+)'", task_description)
        city = city_match.group(1) if city_match else "Mumbai"

        if "name" in desc_lower and "email" in desc_lower:
            return f"SELECT name, email, signup_date FROM customers WHERE city = '{city}' ORDER BY signup_date ASC"
        return f"SELECT * FROM customers WHERE city = '{city}'"

    # Medium: Top N customers by spending
    if "top" in desc_lower and "spent" in desc_lower or "spending" in desc_lower:
        limit_match = re.search(r"top\s+(\d+)", desc_lower)
        limit = int(limit_match.group(1)) if limit_match else 3

        return (
            f"SELECT c.name, SUM(o.total_amount) AS total_spent "
            f"FROM customers c JOIN orders o ON c.id = o.customer_id "
            f"GROUP BY c.id, c.name "
            f"ORDER BY total_spent DESC LIMIT {limit}"
        )

    # Hard: Category-wise top product by revenue
    if "category" in desc_lower and "revenue" in desc_lower:
        return (
            "SELECT p.category, p.name, SUM(oi.quantity * oi.unit_price) AS total_revenue "
            "FROM products p "
            "JOIN order_items oi ON p.id = oi.product_id "
            "GROUP BY p.category, p.name "
            "ORDER BY total_revenue DESC"
        )

    # Fallback
    return "SELECT * FROM customers LIMIT 10"


# ─── LLM-Based Strategy ─────────────────────────────────────────────────────

def llm_inference(task_description: str, schema: str, api_key: str, model: str = "gpt-4o-mini") -> str:
    """
    Generate SQL using an OpenAI-compatible LLM.

    Args:
        task_description: Natural language question
        schema: Database schema DDL
        api_key: OpenAI API key
        model: Model to use (default: gpt-4o-mini)

    Returns:
        Generated SQL query string
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are an expert SQL query writer. Given a database schema and a natural language question, "
        "write a single SQL SELECT query that answers the question. "
        "Return ONLY the SQL query, no explanations or markdown formatting. "
        "Use standard SQLite-compatible SQL syntax."
    )

    user_prompt = f"""Database Schema:
{schema}

Question: {task_description}

Write a single SQL query to answer this question. Return ONLY the SQL, nothing else."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=500,
    )

    sql = response.choices[0].message.content.strip()

    # Clean up: remove markdown code blocks if present
    sql = re.sub(r"^```sql\s*", "", sql)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)
    sql = sql.strip()

    return sql


# ─── Main Inference Loop ─────────────────────────────────────────────────────

TASK_IDS = ["task_easy_001", "task_medium_001", "task_hard_001"]


def run_inference(
    client: SQLQueryEnvHTTPClient,
    strategy: str,
    task_ids: List[str],
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    seed: int = 42,
    max_attempts: int = 3,
) -> Dict[str, float]:
    """
    Run inference across all specified tasks.

    Args:
        client: HTTP client for the environment
        strategy: "rule-based" or "llm"
        task_ids: List of task IDs to evaluate
        api_key: OpenAI API key (required for LLM strategy)
        model: LLM model name
        seed: Random seed for reproducibility
        max_attempts: Max query attempts per task

    Returns:
        Dictionary mapping task_id to best score
    """
    results = {}

    for task_id in task_ids:
        print(f"\n{'='*60}")
        print(f"Task: {task_id}")
        print(f"{'='*60}")

        # Reset with specific task
        reset_result = client.reset(task_id=task_id, seed=seed)
        obs = reset_result.get("observation", {})
        task_desc = obs.get("task_description", "")
        schema = obs.get("schema", "")
        difficulty = obs.get("difficulty", "unknown")

        print(f"Difficulty: {difficulty}")
        print(f"Question: {task_desc}")

        best_score = 0.0

        for attempt in range(1, max_attempts + 1):
            print(f"\n--- Attempt {attempt}/{max_attempts} ---")

            # Generate SQL
            if strategy == "llm":
                sql = llm_inference(task_desc, schema, api_key, model)
            else:
                sql = rule_based_inference(task_desc, schema)

            print(f"Generated SQL: {sql}")

            # Submit via MCP CallToolAction
            step_result = client.step({
                "type": "call_tool",
                "tool_name": "submit_query",
                "arguments": {"sql": sql},
            })

            # Parse response
            step_obs = step_result.get("observation", {})
            reward = step_result.get("reward", 0.0)
            done = step_result.get("done", False)

            # Try to extract tool result
            tool_result = step_obs.get("metadata", {}).get("result", "{}")
            if isinstance(tool_result, str):
                try:
                    tool_data = json.loads(tool_result)
                except json.JSONDecodeError:
                    tool_data = {"feedback": tool_result}
            else:
                tool_data = tool_result

            score = tool_data.get("score", reward or 0.0)
            feedback = tool_data.get("feedback", "No feedback")
            best_score = max(best_score, score)

            print(f"Score: {score:.4f}")
            print(f"Feedback: {feedback}")

            if score >= 1.0 or done:
                break

        results[task_id] = best_score
        print(f"\nBest score for {task_id}: {best_score:.4f}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Baseline inference for SQL Query Environment"
    )
    parser.add_argument(
        "--strategy",
        choices=["rule-based", "llm"],
        default="rule-based",
        help="Inference strategy (default: rule-based)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Environment server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=["all"],
        help="Task IDs to run (default: all)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model name (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max query attempts per task (default: 3)",
    )

    args = parser.parse_args()

    # Resolve task IDs
    task_ids = TASK_IDS if "all" in args.tasks else args.tasks

    # Check API key for LLM strategy
    api_key = None
    if args.strategy == "llm":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY environment variable is required for LLM strategy.")
            print("Set it with: export OPENAI_API_KEY=your-key-here")
            sys.exit(1)

    # Create client
    client = SQLQueryEnvHTTPClient(args.url)

    # Check health
    print("Checking server health...")
    try:
        health = client.health()
        print(f"Server status: {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"ERROR: Cannot connect to server at {args.url}: {e}")
        print("Make sure the server is running: uvicorn server.app:app --port 8000")
        sys.exit(1)

    # Run inference
    print(f"\nStrategy: {args.strategy}")
    print(f"Tasks: {task_ids}")
    print(f"Seed: {args.seed}")
    print(f"Max attempts per task: {args.max_attempts}")

    start_time = time.time()
    results = run_inference(
        client=client,
        strategy=args.strategy,
        task_ids=task_ids,
        api_key=api_key,
        model=args.model,
        seed=args.seed,
        max_attempts=args.max_attempts,
    )
    elapsed = time.time() - start_time

    # Print summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Strategy: {args.strategy}")
    print(f"Time: {elapsed:.1f}s")
    print()

    total_score = 0.0
    for task_id, score in results.items():
        difficulty = "easy" if "easy" in task_id else "medium" if "medium" in task_id else "hard"
        status = "✓" if score >= 1.0 else "△" if score > 0 else "✗"
        print(f"  {status} {task_id} ({difficulty}): {score:.4f}")
        total_score += score

    avg_score = total_score / len(results) if results else 0.0
    print(f"\n  Average Score: {avg_score:.4f}")
    print(f"  Total Score:   {total_score:.4f} / {len(results):.1f}")

    # Save results to file
    output = {
        "strategy": args.strategy,
        "model": args.model if args.strategy == "llm" else None,
        "seed": args.seed,
        "elapsed_seconds": elapsed,
        "results": results,
        "average_score": avg_score,
    }

    os.makedirs("outputs/evals", exist_ok=True)
    output_path = f"outputs/evals/baseline_{args.strategy}_{args.seed}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
