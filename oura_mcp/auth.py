"""One-time OAuth2 helper to obtain an Oura access token for personal use.

Run this script (or `oura-mcp-auth`) the first time, or whenever your token expires.

Prerequisites:
- Create an Oura API application at: https://cloud.ouraring.com/oauth/applications
- In the app settings, add a redirect URI, e.g.:
    http://127.0.0.1:8765/callback
  (or http://localhost:8765/callback)
- Note your Client ID and Client Secret.
- Recommended scopes for full health data: personal daily heartrate workout spo2Daily session tag

The script will:
1. Open your browser to Oura's authorization page.
2. Start a tiny local server to receive the redirect.
3. Exchange the code for tokens.
4. Print your access_token and refresh_token.

Copy the access_token into the OURA_ACCESS_TOKEN environment variable when
starting the MCP server (or store it however you like).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
TOKEN_URL = "https://api.ouraring.com/oauth/token"


class _CallbackHandler(BaseHTTPRequestHandler):
    """Very small HTTP handler that captures the OAuth code."""

    code: str | None = None
    error: str | None = None

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if "code" in qs:
            _CallbackHandler.code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authorization successful!</h1>"
                b"<p>You can close this window and return to the terminal.</p>"
            )
        elif "error" in qs:
            _CallbackHandler.error = qs.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<h1>Error: {_CallbackHandler.error}</h1>".encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):  # noqa: A002
        # Keep the output quiet
        pass


def run_local_callback_server(port: int, timeout: int = 120) -> str:
    """Start a temporary server on localhost and wait for the OAuth redirect.

    Returns the authorization code.
    """
    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"Listening for callback on http://127.0.0.1:{port}/callback ...")
    print("Complete the authorization in your browser.")

    deadline = time.time() + timeout
    while time.time() < deadline:
        if _CallbackHandler.code:
            server.shutdown()
            return _CallbackHandler.code
        if _CallbackHandler.error:
            server.shutdown()
            raise RuntimeError(f"Authorization failed: {_CallbackHandler.error}")
        time.sleep(0.2)

    server.shutdown()
    raise TimeoutError("Timed out waiting for OAuth callback. Did you complete authorization in the browser?")


def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, str]:
    """Exchange authorization code for access + refresh tokens."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()

    if "access_token" not in tokens:
        raise RuntimeError(f"Token exchange failed: {tokens}")

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "expires_in": tokens.get("expires_in"),
        "scope": tokens.get("scope"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Obtain an Oura OAuth2 access token for personal use."
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("OURA_CLIENT_ID"),
        help="Your Oura OAuth application Client ID (or set OURA_CLIENT_ID env var)",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv("OURA_CLIENT_SECRET"),
        help="Your Oura OAuth application Client Secret (or set OURA_CLIENT_SECRET env var)",
    )
    parser.add_argument(
        "--redirect-uri",
        default=os.getenv("OURA_REDIRECT_URI", "http://127.0.0.1:8765/callback"),
        help="Redirect URI registered in your Oura app (must match exactly)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Local port to listen on for the callback (must match redirect URI)",
    )
    parser.add_argument(
        "--scopes",
        default="personal daily heartrate workout spo2Daily session tag",
        help="Space-separated scopes to request (recommended for full health data)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not attempt to open the browser automatically",
    )
    parser.add_argument(
        "--save",
        default="~/.oura_tokens.json",
        help="Optional path to save the tokens as JSON (default: ~/.oura_tokens.json)",
    )

    args = parser.parse_args()

    if not args.client_id or not args.client_secret:
        print("ERROR: You must provide --client-id and --client-secret (or set the env vars).")
        print("Create an app at https://cloud.ouraring.com/oauth/applications")
        sys.exit(1)

    # Build the authorization URL
    auth_params = {
        "client_id": args.client_id,
        "redirect_uri": args.redirect_uri,
        "response_type": "code",
        "scope": args.scopes,
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    print("\n=== Oura OAuth2 Authorization ===\n")
    print("1. Make sure you have registered this redirect URI in your Oura app settings:")
    print(f"   {args.redirect_uri}")
    print("\n2. Opening browser for authorization... (or visit the URL manually)")

    if not args.no_browser:
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass

    print(f"\nAuthorization URL:\n{auth_url}\n")

    # Wait for the callback
    try:
        code = run_local_callback_server(args.port)
    except Exception as exc:
        print(f"\nFailed to receive callback: {exc}")
        sys.exit(1)

    print("\nReceived authorization code. Exchanging for tokens...")

    try:
        tokens = exchange_code_for_tokens(
            args.client_id,
            args.client_secret,
            code,
            args.redirect_uri,
        )
    except Exception as exc:
        print(f"\nToken exchange failed: {exc}")
        sys.exit(1)

    access = tokens["access_token"]
    refresh = tokens.get("refresh_token")

    print("\n" + "=" * 60)
    print("SUCCESS! Here are your tokens:\n")
    print(f"OURA_ACCESS_TOKEN={access}")
    if refresh:
        print(f"OURA_REFRESH_TOKEN={refresh}")
    print("\n" + "=" * 60)

    # Optional save
    save_path = os.path.expanduser(args.save)
    if save_path:
        try:
            payload = {
                "access_token": access,
                "refresh_token": refresh,
                "obtained_at": int(time.time()),
                "scopes": args.scopes,
            }
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w") as f:
                json.dump(payload, f, indent=2)
            print(f"\nTokens also saved to: {save_path}")
            print("You can load them later or set OURA_ACCESS_TOKEN from this file.")
        except Exception as e:
            print(f"\n(Warning: could not save tokens file: {e})")

    print("\nTo use with the MCP server, set the environment variable and start it:")
    print(f'    OURA_ACCESS_TOKEN="{access}" oura-mcp-server')
    print("\nOr with Grok:")
    print(f'    grok mcp add oura -e OURA_ACCESS_TOKEN="{access}" -- oura-mcp-server')
    print("\n(You can also add OURA_REFRESH_TOKEN + client credentials if you want auto-refresh in a future version.)")


if __name__ == "__main__":
    main()
