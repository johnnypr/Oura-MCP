"""Oura Ring API v2 client for the MCP server."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any, Optional

import requests

BASE_URL = "https://api.ouraring.com/v2/usercollection"
DEFAULT_TIMEOUT = 30


class OuraClient:
    """Lightweight client for Oura Cloud API v2.

    Authenticates with a Bearer token (obtained via OAuth2).
    Supports the main personal data endpoints used for health conversations.
    """

    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("access_token is required")
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        })

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """GET with basic pagination support. Returns the full collected response."""
        url = f"{BASE_URL}/{path.lstrip('/')}"
        all_data: list[dict[str, Any]] = []
        next_token: Optional[str] = None
        params = dict(params or {})

        while True:
            if next_token:
                params["next_token"] = next_token

            resp = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()

            data = payload.get("data", [])
            if isinstance(data, list):
                all_data.extend(data)

            next_token = payload.get("next_token")
            if not next_token:
                break

        return {"data": all_data}

    # ---------------------- High-level data accessors ----------------------

    def get_personal_info(self) -> dict[str, Any]:
        """Return the user's personal info (age, gender, height, weight, etc.)."""
        return self._get("personal_info")

    def get_daily_sleep(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Daily sleep summaries (scores, contributors, etc.)."""
        params = self._default_date_params(start_date, end_date)
        return self._get("daily_sleep", params)

    def get_sleep(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Detailed sleep period documents (stages, HR, HRV, respiratory rate, etc.)."""
        params = self._default_date_params(start_date, end_date)
        return self._get("sleep", params)

    def get_daily_readiness(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Daily readiness scores and contributors."""
        params = self._default_date_params(start_date, end_date)
        return self._get("daily_readiness", params)

    def get_daily_activity(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Daily activity summaries (steps, active calories, movement, etc.)."""
        params = self._default_date_params(start_date, end_date)
        return self._get("daily_activity", params)

    def get_heart_rate(
        self,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None,
    ) -> dict[str, Any]:
        """Heart rate time series (5-min buckets during sleep + daytime samples).

        Use ISO 8601 datetimes, e.g. "2025-06-10T00:00:00-07:00".
        If omitted, defaults to the last 7 days.
        """
        params: dict[str, Any] = {}
        today = date.today()
        if not start_datetime:
            start_dt = datetime.combine(today - timedelta(days=7), datetime.min.time())
            start_datetime = start_dt.isoformat()
        if not end_datetime:
            end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())
            end_datetime = end_dt.isoformat()

        params["start_datetime"] = start_datetime
        params["end_datetime"] = end_datetime
        return self._get("heartrate", params)

    def get_workouts(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        params = self._default_date_params(start_date, end_date)
        return self._get("workout", params)

    def get_sessions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Guided/unguided sessions (rest, meditation, etc.) and tags."""
        params = self._default_date_params(start_date, end_date)
        return self._get("session", params)

    # ---------------------- Helpers ----------------------

    def _default_date_params(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> dict[str, str]:
        today = date.today()
        if not end_date:
            end_date = today.isoformat()
        if not start_date:
            start_date = (today - timedelta(days=7)).isoformat()
        return {"start_date": start_date, "end_date": end_date}

    def get_latest_summary(self, days: int = 3) -> dict[str, Any]:
        """Convenience: fetch the most recent N days of daily_sleep + daily_readiness + daily_activity.

        Returns a compact dict with the three latest records per category.
        """
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=days)).isoformat()

        sleep = self.get_daily_sleep(start, end).get("data", [])
        readiness = self.get_daily_readiness(start, end).get("data", [])
        activity = self.get_daily_activity(start, end).get("data", [])

        return {
            "period": f"{start} to {end}",
            "daily_sleep": sleep[-days:] if sleep else [],
            "daily_readiness": readiness[-days:] if readiness else [],
            "daily_activity": activity[-days:] if activity else [],
        }
