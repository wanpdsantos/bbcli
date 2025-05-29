"""
OAuth 2.0 authentication commands for bbcli.

This module provides commands for managing OAuth 2.0 authentication with Bitbucket,
including OAuth app setup, login, logout, and status checking.
"""

import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import click
from rich.console import Console

from bbcli.core.api_client import BitbucketAPIClient
from bbcli.core.exceptions import AuthenticationError, BBCLIError
from bbcli.core.oauth_manager import OAuthApp, OAuthManager
from bbcli.core.oauth_storage import OAuthStorage
from bbcli.utils.output import OutputFormatter


class OAuthCallbackServer(HTTPServer):
    """Custom HTTP server with OAuth callback attributes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_received: bool = False
        self.authorization_code: str | None = None
        self.state: str | None = None
        self.error: str | None = None


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    server: OAuthCallbackServer  # Type annotation for the server

    def do_GET(self):
        """Handle GET request for OAuth callback."""
        # Parse the callback URL
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        # Store the authorization code and state
        self.server.authorization_code = query_params.get("code", [None])[0]
        self.server.state = query_params.get("state", [None])[0]
        self.server.error = query_params.get("error", [None])[0]

        # Send response to browser
        if self.server.error:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"""
                <html><body>
                <h1>Authentication Failed</h1>
                <p>There was an error during authentication. You can close this window.</p>
                </body></html>
            """
            )
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"""
                <html><body>
                <h1>Authentication Successful</h1>
                <p>You can now close this window and return to the terminal.</p>
                </body></html>
            """
            )

        self.server.callback_received = True


@click.group()
def oauth() -> None:
    """Manage OAuth 2.0 authentication with Bitbucket."""


@oauth.command()
@click.option("--client-id", required=True, help="OAuth app client ID")
@click.option("--client-secret", required=True, help="OAuth app client secret")
@click.option(
    "--redirect-uri",
    default="http://localhost:8080/callback",
    help="OAuth redirect URI",
)
@click.option("--scopes", help="Comma-separated list of OAuth scopes")
@click.pass_context
def setup(
    ctx: click.Context,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: str,
) -> None:
    """
    Set up OAuth 2.0 app credentials.

    Before using OAuth authentication, you need to create an OAuth app in Bitbucket:
    1. Go to https://bitbucket.org/account/settings/app-passwords/
    2. Click "OAuth" tab
    3. Click "Add consumer"
    4. Fill in the details and set the callback URL
    5. Copy the client ID and secret
    """
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        oauth_storage = OAuthStorage()

        # Create OAuth app configuration
        oauth_app = OAuthApp(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
        )

        # Store the OAuth app configuration
        if oauth_storage.store_oauth_app(oauth_app):
            formatter.success(
                "OAuth app configuration saved successfully!",
                details={
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "scopes": scopes or "default",
                    "storage": oauth_storage.get_storage_info()["storage_type"],
                },
            )
        else:
            raise BBCLIError("Failed to store OAuth app configuration")

    except Exception as e:
        formatter.error(f"Failed to set up OAuth app: {e}")
        sys.exit(1)


@oauth.command()
@click.option("--port", default=8080, help="Local port for OAuth callback")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
@click.pass_context
def login(ctx: click.Context, port: int, no_browser: bool) -> None:
    """
    Authenticate using OAuth 2.0 Authorization Code flow.

    This will open your browser to authenticate with Bitbucket and store
    the access token securely for future use.
    """
    console: Console = ctx.obj["console"]
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        oauth_storage = OAuthStorage()
        oauth_manager = OAuthManager()

        # Check if OAuth app is configured
        oauth_app = oauth_storage.get_oauth_app()
        if not oauth_app:
            raise BBCLIError(
                "OAuth app not configured. Run 'bbcli oauth setup' first.",
                suggestion="Use 'bbcli oauth setup --help' for more information",
            )

        # Update redirect URI to use the specified port
        oauth_app.redirect_uri = f"http://localhost:{port}/callback"

        console.print("🔐 Starting OAuth 2.0 authentication flow...")

        # Generate authorization URL
        auth_url, code_verifier, state = oauth_manager.build_authorization_url(oauth_app)

        console.print(f"📱 Authorization URL: {auth_url}")

        if not no_browser:
            console.print("🌐 Opening browser...")
            webbrowser.open(auth_url)
        else:
            console.print("Please open the above URL in your browser to authenticate.")

        # Start local HTTP server to receive callback
        server = OAuthCallbackServer(("localhost", port), CallbackHandler)

        console.print(f"🔄 Waiting for callback on http://localhost:{port}/callback...")

        # Handle requests until callback is received
        while not server.callback_received:
            server.handle_request()

        server.server_close()

        # Check for errors
        if server.error:
            raise BBCLIError(f"OAuth authentication failed: {server.error}")

        if not server.authorization_code:
            raise BBCLIError("No authorization code received")

        if server.state != state:
            raise BBCLIError("Invalid state parameter - possible CSRF attack")

        console.print("✅ Authorization code received, exchanging for access token...")

        # Exchange authorization code for access token
        token = oauth_manager.exchange_code_for_token(oauth_app, server.authorization_code, code_verifier)

        # Store the token
        if oauth_storage.store_oauth_token(token):
            console.print("💾 Access token stored securely")

            # Test the token
            console.print("🔍 Testing authentication...")
            api_client = BitbucketAPIClient(oauth_token=token.access_token)
            user_info = api_client.test_authentication()

            formatter.success(
                "OAuth 2.0 authentication successful!",
                details={
                    "username": user_info.get("username", "Unknown"),
                    "display_name": user_info.get("display_name", "Unknown"),
                    "token_type": token.token_type,
                    "expires_in": (f"{token.expires_in} seconds" if token.expires_in else "No expiration"),
                    "scopes": token.scope or "default",
                    "storage": oauth_storage.get_storage_info()["storage_type"],
                },
            )
        else:
            raise BBCLIError("Failed to store access token")

    except BBCLIError as e:
        formatter.error(str(e), details={"suggestion": e.suggestion} if e.suggestion else None)
        sys.exit(e.exit_code)
    except Exception as e:
        formatter.error(f"OAuth authentication failed: {e}")
        sys.exit(1)


@oauth.command()
@click.pass_context
def logout(ctx: click.Context) -> None:
    """Remove stored OAuth tokens and app configuration."""
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        oauth_storage = OAuthStorage()

        if not oauth_storage.has_any_oauth_data():
            formatter.info("No OAuth data found")
            return

        # Confirm logout
        if click.confirm("Are you sure you want to remove all OAuth data?"):
            if oauth_storage.clear_all_oauth_data():
                formatter.success("OAuth data removed successfully")
            else:
                formatter.warning("Some OAuth data could not be removed")
        else:
            formatter.info("Logout cancelled")

    except Exception as e:
        raise BBCLIError(f"Failed to remove OAuth data: {e}") from e


@oauth.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check OAuth authentication status."""
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        oauth_storage = OAuthStorage()

        # Check OAuth app configuration
        oauth_app = oauth_storage.get_oauth_app()
        if not oauth_app:
            formatter.info("OAuth app not configured")
            formatter.info("Run 'bbcli oauth setup' to configure OAuth authentication")
            return

        # Check OAuth token
        oauth_token = oauth_storage.get_oauth_token()
        if not oauth_token:
            formatter.info("No OAuth token found")
            formatter.info("Run 'bbcli oauth login' to authenticate")
            return

        # Test current token
        try:
            api_client = BitbucketAPIClient(oauth_token=oauth_token.access_token)
            user_info = api_client.test_authentication()

            status_info = {
                "status": "Authenticated (OAuth 2.0)",
                "username": user_info.get("username", "Unknown"),
                "display_name": user_info.get("display_name", "Unknown"),
                "account_id": user_info.get("account_id", "Unknown"),
                "client_id": oauth_app.client_id,
                "token_type": oauth_token.token_type,
                "expires_in": (f"{oauth_token.expires_in} seconds" if oauth_token.expires_in else "No expiration"),
                "is_expired": oauth_token.is_expired,
                "scopes": oauth_token.scope or "default",
                "storage": oauth_storage.get_storage_info()["storage_type"],
            }

            formatter.format_output(status_info, "OAuth Authentication Status")

        except AuthenticationError:
            formatter.error(
                "Stored OAuth token is invalid or expired",
                details={"suggestion": "Run 'bbcli oauth login' to re-authenticate"},
            )

    except Exception as e:
        raise BBCLIError(f"Failed to check OAuth status: {e}") from e
