"""
Authentication commands for bbcli.

This module provides commands for managing authentication with Bitbucket,
including OAuth 2.0 login, logout, and status checking.
"""

import getpass
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import click
from rich.console import Console
from rich.panel import Panel

from bbcli.core.api_client import BitbucketAPIClient, get_api_client
from bbcli.core.auth_manager import AuthManager
from bbcli.core.exceptions import AuthenticationError, BBCLIError
from bbcli.core.oauth_manager import OAuthManager
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

        # Signal that we're done
        self.server.callback_received = True


@click.group()
def auth() -> None:
    """Manage authentication with Bitbucket."""
    pass


@auth.command()
@click.option("--port", default=8080, help="Local port for OAuth callback")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
@click.pass_context
def login(ctx: click.Context, port: int, no_browser: bool) -> None:
    """
    Authenticate with Bitbucket using OAuth 2.0.

    This command will open your browser to authenticate with Bitbucket and store
    the access token securely for future use. This is the recommended authentication
    method as it's more secure than app passwords.

    The authentication flow:
    1. Opens your browser to Bitbucket's OAuth authorization page
    2. You log in with your Bitbucket credentials
    3. Bitbucket redirects back to a local server with an authorization code
    4. The code is exchanged for an access token
    5. The token is stored securely for future API calls

    If you prefer app passwords, use 'bbcli auth login-basic' instead.
    """
    console: Console = ctx.obj["console"]
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        oauth_storage = OAuthStorage()
        oauth_manager = OAuthManager()

        # Check if OAuth app is configured, if not, set up a default one
        oauth_app = oauth_storage.get_oauth_app()
        if not oauth_app:
            console.print("🔧 Setting up OAuth configuration...")

            # OAuth app configuration is required - users must create their own OAuth app
            # We don't provide default credentials for security reasons

            # For now, show instructions to create OAuth app
            instructions = f"""
To use OAuth authentication, you need to create an OAuth app in Bitbucket:

1. Go to https://bitbucket.org/account/settings/app-passwords/
2. Click the "OAuth" tab
3. Click "Add consumer"
4. Fill in the details:
   • Name: bbcli (or any descriptive name)
   • Callback URL: http://localhost:{port}/callback
   • Permissions: Account (Read), Repositories (Read, Write, Admin), Projects (Read, Write, Admin)
5. Copy the Client ID and Client Secret
6. Run: bbcli oauth setup --client-id YOUR_ID --client-secret YOUR_SECRET

For now, falling back to basic authentication...
            """

            console.print(
                Panel(
                    instructions.strip(),
                    title="OAuth Setup Required",
                    border_style="yellow",
                )
            )
            console.print()

            # Fall back to basic auth setup
            return _setup_basic_auth(console, formatter)

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


def _setup_basic_auth(console: Console, formatter: OutputFormatter) -> None:
    """Set up basic authentication as fallback."""
    try:
        auth_manager = AuthManager()

        # Show instructions for creating App Password
        instructions = """
To create a Bitbucket App Password:

1. Log in to Bitbucket (https://bitbucket.org)
2. Go to your Avatar > Personal settings
3. Navigate to "App passwords" under "Access management"
4. Click "Create app password"
5. Give it a descriptive label (e.g., 'bbcli_access')
6. Grant the necessary permissions:
   • Projects: Read, Write, Admin
   • Repositories: Read, Write, Admin
   • Account: Read
   • Pull Requests: Read, Write
   • Branching: Read, Write
7. Copy the generated password (you won't see it again)
        """

        console.print(Panel(instructions.strip(), title="App Password Setup", border_style="blue"))
        console.print()

        # Prompt for credentials
        console.print("[cyan]Note:[/cyan] Use your Bitbucket username (not email) for authentication")
        console.print("[dim]To find your username: Go to bitbucket.org → Profile → Your username is in the URL[/dim]")
        username = click.prompt("Enter your Bitbucket username", type=str)
        app_password = getpass.getpass("Enter your Bitbucket App Password: ")

        if not username or not app_password:
            raise BBCLIError("Username and App Password are required")

        # Test credentials
        console.print("🔍 Testing credentials...")

        # Create a temporary API client with the provided credentials for testing
        api_client = BitbucketAPIClient(username=username, password=app_password, prefer_oauth=False)

        try:
            user_info = api_client.test_authentication()
            console.print(f"✅ Authentication successful for user: {user_info.get('display_name', username)}")
        except AuthenticationError as e:
            # Provide specific guidance based on common issues
            suggestion = "Ensure your App Password has the required permissions"
            if "@" in username:
                suggestion = "Use your Bitbucket username (not email address) for authentication. " + suggestion
            elif len(username) < 3:
                suggestion = "Username seems too short. Make sure you're using your full Bitbucket username. " + suggestion

            raise BBCLIError(
                "Authentication failed. Please check your username and App Password.",
                suggestion=suggestion,
            ) from e

        # Store credentials securely
        console.print("💾 Storing credentials securely...")
        auth_manager.store_credentials(username, app_password)

        formatter.success(
            "Basic authentication setup complete!",
            details={
                "username": username,
                "storage": ("System keyring" if auth_manager._keyring_available else "Encrypted local file"),
            },
        )

    except BBCLIError as e:
        # Re-raise BBCLIError as-is (these have user-friendly messages)
        formatter.error(str(e), details={"suggestion": e.suggestion} if e.suggestion else None)
        sys.exit(e.exit_code)
    except Exception as e:
        # Handle unexpected errors
        formatter.error(f"Failed to set up authentication: {e}")
        sys.exit(1)


@auth.command("login-basic")
@click.pass_context
def login_basic(ctx: click.Context) -> None:
    """
    Set up basic authentication with Bitbucket App Password.

    This is an alternative authentication method using username and app password.
    OAuth 2.0 (bbcli auth login) is recommended for better security.
    """
    console: Console = ctx.obj["console"]
    formatter: OutputFormatter = ctx.obj["formatter"]

    _setup_basic_auth(console, formatter)


@auth.command()
@click.pass_context
def logout(ctx: click.Context) -> None:
    """Remove stored authentication credentials."""
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        auth_manager = AuthManager()

        if not auth_manager.has_credentials():
            formatter.info("No stored credentials found")
            return

        # Confirm logout
        if click.confirm("Are you sure you want to remove stored credentials?"):
            if auth_manager.delete_credentials():
                formatter.success("Credentials removed successfully")
            else:
                formatter.warning("No credentials were found to remove")
        else:
            formatter.info("Logout cancelled")

    except Exception as e:
        raise BBCLIError(f"Failed to remove credentials: {e}") from e


@auth.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check authentication status."""
    formatter: OutputFormatter = ctx.obj["formatter"]

    try:
        auth_manager = AuthManager()
        oauth_storage = OAuthStorage()

        # Check both Basic Auth and OAuth
        has_basic_auth = auth_manager.has_credentials()
        has_oauth = oauth_storage.has_oauth_token()

        if not has_basic_auth and not has_oauth:
            formatter.info("Not authenticated")
            formatter.info("Run 'bbcli auth login' to authenticate with OAuth 2.0 (recommended)")
            formatter.info("Or run 'bbcli auth login-basic' for App Password authentication")
            return

        # Test current credentials
        try:
            api_client = get_api_client()
            user_info = api_client.test_authentication()

            # Determine which authentication method is being used
            auth_method = "OAuth 2.0" if api_client.is_using_oauth() else "Basic Auth (App Password)"

            status_info = {
                "status": f"Authenticated ({auth_method})",
                "username": user_info.get("username", "Unknown"),
                "display_name": user_info.get("display_name", "Unknown"),
                "account_id": user_info.get("account_id", "Unknown"),
                "has_basic_auth": has_basic_auth,
                "has_oauth": has_oauth,
                "using_oauth": api_client.is_using_oauth(),
                "storage": ("System keyring" if auth_manager._keyring_available else "Encrypted local file"),
            }

            # Add OAuth-specific information if available
            if has_oauth:
                oauth_token = oauth_storage.get_oauth_token()
                if oauth_token:
                    status_info.update(
                        {
                            "oauth_token_type": oauth_token.token_type,
                            "oauth_expires_in": (
                                f"{oauth_token.expires_in} seconds" if oauth_token.expires_in else "No expiration"
                            ),
                            "oauth_is_expired": oauth_token.is_expired,
                            "oauth_scopes": oauth_token.scope or "default",
                        }
                    )

            formatter.format_output(status_info, "Authentication Status")

        except AuthenticationError:
            formatter.error(
                "Stored credentials are invalid or expired",
                details={"suggestion": "Run 'bbcli auth login' to re-authenticate with OAuth 2.0"},
            )

    except Exception as e:
        raise BBCLIError(f"Failed to check authentication status: {e}") from e
