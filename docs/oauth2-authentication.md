# OAuth 2.0 Authentication for bbcli

This document describes the OAuth 2.0 authentication implementation in bbcli, which provides a more secure and modern alternative to Basic Authentication with App Passwords.

## Overview

bbcli now supports OAuth 2.0 authentication alongside the existing Basic Authentication method. OAuth 2.0 provides several advantages:

- **Enhanced Security**: No need to store passwords; uses secure access tokens
- **Fine-grained Permissions**: Scope-based access control
- **Token Expiration**: Automatic token expiration with refresh capability
- **Revocable Access**: Tokens can be revoked without changing passwords

## Supported OAuth 2.0 Flows

### 1. Authorization Code Grant (Recommended)
The full OAuth 2.0 flow with PKCE (Proof Key for Code Exchange) for enhanced security:
- Interactive browser-based authentication
- Secure code exchange with PKCE
- Refresh token support for long-term access

### 2. Client Credentials Grant
For server-to-server authentication:
- Non-interactive authentication
- Suitable for automated scripts and CI/CD pipelines
- Uses client ID and secret directly

## Setting Up OAuth 2.0

### Step 1: Create an OAuth App in Bitbucket

1. Go to [Bitbucket OAuth Settings](https://bitbucket.org/account/settings/app-passwords/)
2. Click the "OAuth" tab
3. Click "Add consumer"
4. Fill in the required details:
   - **Name**: A descriptive name (e.g., "bbcli CLI Tool")
   - **Description**: Optional description
   - **Callback URL**: `http://localhost:8080/callback` (or your preferred port)
   - **URL**: Your application URL (optional)
5. Select the required permissions/scopes:
   - **Account**: Read (required for user info)
   - **Repositories**: Read, Write, Admin (as needed)
   - **Projects**: Read, Write, Admin (as needed)
   - **Pull requests**: Read, Write (as needed)
   - **Webhooks**: Read, Write (if needed)
6. Click "Save"
7. Copy the generated **Client ID** and **Client Secret**

### Step 2: Configure bbcli with OAuth Credentials

```bash
bbcli oauth setup \
  --client-id "your_client_id" \
  --client-secret "your_client_secret" \
  --redirect-uri "http://localhost:8080/callback" \
  --scopes "account,repository,repository:write,pullrequest,pullrequest:write,project"
```

### Step 3: Authenticate

```bash
bbcli oauth login
```

This will:
1. Open your default browser to Bitbucket's authorization page
2. Start a local HTTP server to receive the callback
3. Exchange the authorization code for an access token
4. Store the token securely (encrypted locally or in system keyring)
5. Test the authentication

## Using OAuth 2.0 Authentication

### Command Line Usage

Once configured, bbcli will automatically use OAuth 2.0 for API requests:

```bash
# Check authentication status
bbcli auth status

# Use any bbcli command - OAuth will be used automatically
bbcli repo list
bbcli project create MYPROJ
bbcli repo create my-new-repo
```

### Environment Variables

You can also provide OAuth tokens via environment variables:

```bash
export BBCLI_OAUTH_TOKEN="your_access_token"
bbcli repo list
```

### Programmatic Usage

```python
from bbcli.core.api_client import BitbucketAPIClient

# Using OAuth token
client = BitbucketAPIClient(oauth_token="your_access_token")

# OAuth is preferred over Basic Auth by default
client = BitbucketAPIClient(
    username="user",
    password="pass",
    oauth_token="token",
    prefer_oauth=True  # Default
)
```

## Authentication Priority

bbcli uses the following priority order for authentication:

1. **OAuth 2.0 Bearer Token** (if `prefer_oauth=True` and token available)
2. **Basic Authentication** (username/password or app password)

### Sources Priority (for each method):

**OAuth Token Sources:**
1. Constructor parameter (`oauth_token`)
2. Environment variable (`BBCLI_OAUTH_TOKEN`)
3. Stored token (if valid and not expired)

**Basic Auth Sources:**
1. Constructor parameters (`username`, `password`)
2. Environment variables (`BBCLI_USERNAME`, `BBCLI_PASSWORD`)
3. Stored credentials

## Token Management

### Token Storage
- Tokens are stored securely using the same mechanism as Basic Auth credentials
- **System Keyring** (preferred): macOS Keychain, Windows Credential Manager, Linux Secret Service
- **Encrypted Local File** (fallback): AES-256 encrypted file in user config directory

### Token Expiration and Refresh
- Access tokens typically expire in 1 hour
- Refresh tokens are used automatically to obtain new access tokens
- If refresh fails, you'll need to re-authenticate with `bbcli oauth login`

### Token Revocation
```bash
# Remove stored OAuth tokens and app configuration
bbcli oauth logout
```

## OAuth 2.0 Commands

### `bbcli oauth setup`
Configure OAuth app credentials.

**Options:**
- `--client-id`: OAuth app client ID (required)
- `--client-secret`: OAuth app client secret (required)
- `--redirect-uri`: OAuth redirect URI (default: `http://localhost:8080/callback`)
- `--scopes`: Comma-separated list of OAuth scopes

### `bbcli oauth login`
Authenticate using OAuth 2.0 Authorization Code flow.

**Options:**
- `--port`: Local port for OAuth callback (default: 8080)
- `--no-browser`: Don't open browser automatically

### `bbcli oauth status`
Check OAuth authentication status and token information.

### `bbcli oauth logout`
Remove stored OAuth tokens and app configuration.

## Security Considerations

### PKCE (Proof Key for Code Exchange)
bbcli implements PKCE by default for the Authorization Code flow, which provides additional security against authorization code interception attacks.

### Local HTTP Server
During the OAuth flow, bbcli starts a temporary local HTTP server to receive the authorization callback. This server:
- Only listens on localhost
- Automatically shuts down after receiving the callback
- Uses a random state parameter to prevent CSRF attacks

### Token Storage
- Tokens are encrypted before storage
- System keyring is preferred over local files
- Tokens are never logged or displayed in plain text

## Troubleshooting

### Common Issues

**"OAuth app not configured"**
- Run `bbcli oauth setup` with your OAuth app credentials

**"No authorization code received"**
- Check that the redirect URI matches your OAuth app configuration
- Ensure the callback port is not blocked by firewall
- Try using `--no-browser` and manually opening the authorization URL

**"Token expired" or "Invalid token"**
- Run `bbcli oauth login` to re-authenticate
- Check that your OAuth app is still active in Bitbucket

**"Permission denied" errors**
- Verify that your OAuth app has the required scopes/permissions
- Re-run `bbcli oauth setup` with appropriate scopes

### Debug Mode
Enable debug mode for detailed OAuth flow information:

```bash
export BBCLI_DEBUG=1
bbcli oauth login
```

## Migration from Basic Auth

OAuth 2.0 and Basic Auth can coexist. To migrate:

1. Set up OAuth 2.0 as described above
2. Test OAuth authentication: `bbcli oauth status`
3. Verify API access works: `bbcli repo list`
4. Optionally remove Basic Auth credentials: `bbcli auth logout`

## API Reference

### OAuth Manager Classes

- `OAuthManager`: Handles OAuth 2.0 flows and token operations
- `OAuthStorage`: Secure storage and retrieval of OAuth tokens and app credentials
- `OAuthToken`: Token data structure with expiration handling
- `OAuthApp`: OAuth application configuration

### API Client Integration

The `BitbucketAPIClient` class automatically handles OAuth 2.0 authentication when tokens are available, with seamless fallback to Basic Auth when needed.
