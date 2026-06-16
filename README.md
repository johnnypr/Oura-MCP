# oura-mcp

A Python MCP server that lets Grok (and other MCP clients) pull your personal Oura Ring health data directly from the official Oura Cloud API v2.

Use it to have natural conversations like:
- "How was my sleep last night?"
- "What's my readiness trend over the last 10 days?"
- "Compare my activity and sleep scores this week."
- "Did my heart rate drop nicely during last night's deep sleep?"

## Features

- Clean, LLM-friendly tools for the most useful Oura data:
  - Personal profile
  - Detailed sleep + daily sleep summaries
  - Daily readiness (score + 9 contributors)
  - Daily activity (steps, calories, movement)
  - Heart rate time series
  - Workouts and sessions/tags
  - A convenient `get_latest_health_summary` aggregator
- Automatic pagination handling
- Sensible date defaults (last 7 days when you don't specify)
- Works with Grok's `search_tool` / `use_tool` mechanism

## Requirements

- Python 3.10+
- An Oura account + Ring
- An Oura OAuth2 application (see setup below)

> **Note on authentication**: Personal Access Tokens (PATs) were deprecated by Oura in December 2025. This server uses the modern OAuth2 flow.

## Quick Setup

### 1. Create an Oura API Application (one-time)

1. Go to https://cloud.ouraring.com/oauth/applications
2. Create a new application.
3. Add a redirect URI for local use, for example:
   - `http://127.0.0.1:8765/callback`
   - or `http://localhost:8765/callback`
4. Copy the **Client ID** and **Client Secret**.
5. In the app settings, select the scopes you want to allow (recommended for rich health conversations):
   - `personal`
   - `daily`
   - `heartrate`
   - `workout`
   - `spo2Daily`
   - `session`
   - `tag`

### 2. Get Your Access Token

Clone or download this repo, then run the included auth helper:

```bash
cd /path/to/oura-mcp

# Using uv (recommended)
uv run oura-mcp-auth \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET \
  --redirect-uri "http://127.0.0.1:8765/callback"

# Or with pip-installed editable copy
pip install -e .
oura-mcp-auth --client-id ... --client-secret ...
```

- It will open your browser to Oura's authorization page.
- Log in and approve the requested scopes.
- The script captures the redirect locally and exchanges the code for tokens.
- It prints your `OURA_ACCESS_TOKEN` (and a refresh token if available).
- Tokens are also saved to `~/.oura_tokens.json` by default.

### 3. Add the MCP Server to Grok

Use the convenient `grok mcp add` command (recommended):

```bash
# After you have the access token from step 2
grok mcp add oura \
  -e OURA_ACCESS_TOKEN="paste-your-access-token-here" \
  -- oura-mcp-server
```

If the `oura-mcp-server` command is not on your PATH after `pip install -e .`, use the module form instead (more reliable):

```bash
grok mcp add oura \
  -e OURA_ACCESS_TOKEN="paste-your-access-token-here" \
  -- python3 -m oura_mcp.server
```

Or manually edit `~/.grok/config.toml`:

```toml
[mcp_servers.oura]
command = "python3"
args = ["-m", "oura_mcp.server"]
env = { OURA_ACCESS_TOKEN = "your-access-token" }
enabled = true
```

You can also launch it directly for testing:

```bash
OURA_ACCESS_TOKEN="your-token" python3 -m oura_mcp.server
```

After adding, restart Grok or press `r` in the `/mcps` modal to refresh the server list. You should see new tools like `oura__get_daily_readiness`, `oura__get_latest_health_summary`, etc.

### 4. Chat about your health!

Examples:

- "Pull my latest readiness and sleep data and summarize how I've been recovering."
- "Show me my heart rate during sleep last night and tell me if there were any spikes."
- "Compare my step count and sleep efficiency for the past 5 days."
- "What's my current readiness score and what are the biggest contributors dragging it down?"

Grok will automatically discover and call the right tools using `search_tool` then `use_tool`.

## Available Tools

| Tool                        | Description                                      | Date params                  |
|-----------------------------|--------------------------------------------------|------------------------------|
| `get_personal_info`         | Profile (age/gender/height/weight)               | —                            |
| `get_sleep_data`            | Detailed per-sleep-period records                | start_date / end_date        |
| `get_daily_sleep`           | Daily sleep scores + contributors                | start_date / end_date        |
| `get_daily_readiness`       | Daily readiness scores + 9 contributors          | start_date / end_date        |
| `get_daily_activity`        | Steps, calories, activity minutes, etc.          | start_date / end_date        |
| `get_heart_rate_data`       | 5-min heart rate time series                     | start_datetime / end_datetime|
| `get_workouts`              | Auto-detected + manual workouts                  | start_date / end_date        |
| `get_sessions`              | Rest/meditation sessions + tags                  | start_date / end_date        |
| `get_latest_health_summary` | Aggregated recent daily sleep/readiness/activity | `days` (default 7)           |

All date parameters are optional. When omitted the tools default to the last 7 days (or equivalent).

## Development / Running Locally

```bash
# Install in editable mode
uv pip install -e ".[dev]"

# Run the server directly
OURA_ACCESS_TOKEN=... uv run oura-mcp-server

# Run the auth helper
uv run oura-mcp-auth --help
```

## Token Refresh (Advanced)

Access tokens eventually expire. The auth helper gives you a `refresh_token`.

A future version of this server can auto-refresh using `OURA_REFRESH_TOKEN`, `OURA_CLIENT_ID`, and `OURA_CLIENT_SECRET`. For now, simply re-run `oura-mcp-auth` when needed and update the `OURA_ACCESS_TOKEN` value in your Grok config or environment.

## Security Notes

- Never commit tokens to git.
- The local OAuth callback server only listens on localhost.
- Only request the scopes you actually need.
- You can revoke access at any time from your Oura account settings.

## Troubleshooting

- **"OURA_ACCESS_TOKEN environment variable is not set"** — Make sure you passed `-e` correctly to `grok mcp add` or exported the variable before running the server.
- **401 Unauthorized** — Token expired or revoked. Re-run the auth helper.
- **No data / empty arrays** — Make sure your ring has synced recently in the Oura app. Some data types (especially detailed sleep) only appear after you open the app and sync.
- **Redirect URI mismatch** — The URI you pass to the auth script must be *exactly* the same as the one registered in the Oura developer console.
- Check server logs: `tail -f ~/.grok/logs/mcp/oura.stderr.log` (Grok captures stderr from MCP servers).

## License

MIT-style. Use freely for personal health tracking.

## Credits

Built for use with Grok Build / xAI. Data provided by the Oura Cloud API v2.

Enjoy understanding your recovery, sleep, and activity data through conversation!
