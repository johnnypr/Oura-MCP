"""FastMCP server exposing Oura Ring health data as tools."""

from __future__ import annotations

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .client import OuraClient

mcp = FastMCP("Oura Ring")

# Lazy singleton client (token comes from env at first use)
_client: Optional[OuraClient] = None


def _get_client() -> OuraClient:
    global _client
    if _client is None:
        token = os.getenv("OURA_ACCESS_TOKEN")
        if not token:
            raise RuntimeError(
                "OURA_ACCESS_TOKEN environment variable is not set. "
                "Set it to your Oura OAuth2 access token before starting the server. "
                "Run 'oura-mcp-auth' (or see README) to obtain one."
            )
        _client = OuraClient(token)
    return _client


def _to_json(obj: object) -> str:
    """Return pretty JSON for tool responses (easy for the LLM to read + parse)."""
    return json.dumps(obj, indent=2, default=str)


# ----------------------------- TOOLS -----------------------------

@mcp.tool()
def get_personal_info() -> str:
    """Return basic profile information from your Oura account (age range, gender, height, weight, etc.).

    Use this when the user asks about their profile, age, or basic settings.
    """
    client = _get_client()
    return _to_json(client.get_personal_info())


@mcp.tool()
def get_sleep_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Fetch detailed sleep period data.

    Each record includes sleep score, stages (deep/light/rem/awake), efficiency, latency,
    average HR/HRV/respiratory rate, bedtime, time in bed, disturbances, etc.

    Dates are YYYY-MM-DD. If omitted, defaults to the last 7 days.
    """
    client = _get_client()
    data = client.get_sleep(start_date, end_date)
    return _to_json(data)


@mcp.tool()
def get_daily_sleep(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Fetch daily sleep summaries (one row per night with overall score + contributors).

    Great for trends: "How has my sleep score been this week?"
    """
    client = _get_client()
    data = client.get_daily_sleep(start_date, end_date)
    return _to_json(data)


@mcp.tool()
def get_daily_readiness(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Fetch daily readiness scores and the 9 contributors (HRV balance, sleep balance, etc.).

    Readiness tells you how ready your body is to perform.
    """
    client = _get_client()
    data = client.get_daily_readiness(start_date, end_date)
    return _to_json(data)


@mcp.tool()
def get_daily_activity(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Fetch daily activity summaries: steps, active calories, sedentary time,
    low/medium/high activity minutes, MET minutes, etc.
    """
    client = _get_client()
    data = client.get_daily_activity(start_date, end_date)
    return _to_json(data)


@mcp.tool()
def get_heart_rate_data(
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
) -> str:
    """Fetch heart rate time series (BPM samples, usually 5-minute resolution).

    Use full ISO datetimes when you need precise windows (e.g. during a specific night).
    If omitted, returns the last ~7 days.
    """
    client = _get_client()
    data = client.get_heart_rate(start_datetime, end_datetime)
    return _to_json(data)


@mcp.tool()
def get_workouts(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Fetch detected and manually logged workouts (duration, calories, HR zones if available)."""
    client = _get_client()
    data = client.get_workouts(start_date, end_date)
    return _to_json(data)


@mcp.tool()
def get_latest_health_summary(days: int = 7) -> str:
    """Convenience tool: returns the most recent N days of daily sleep + readiness + activity in one call.

    Perfect starting point for "How have I been doing the last week?" or "Summarize my recent health".
    """
    client = _get_client()
    summary = client.get_latest_summary(days)
    return _to_json(summary)


@mcp.tool()
def get_sessions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Fetch sessions (rest, meditation, breathing exercises) and any user tags."""
    client = _get_client()
    data = client.get_sessions(start_date, end_date)
    return _to_json(data)


# ----------------------------- ENTRYPOINT -----------------------------

def main() -> None:
    """Run the MCP server over stdio (the transport Grok uses)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
