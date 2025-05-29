# Enhanced Basic HTTP Authentication

This document describes the enhanced Basic HTTP Authentication features implemented in the bbcli API client.

## Overview

The BitbucketAPIClient now supports multiple authentication methods with a clear priority order and enhanced error handling. All HTTP requests use proper Basic HTTP Authentication with Base64-encoded credentials.

**✅ FIXED**: The issue where `bbcli auth login` credentials weren't being used has been resolved. The API client now properly adds `Authorization: Basic <encoded-credentials>` headers to all HTTP requests.

## Authentication Methods

### 1. Constructor Parameters (Highest Priority)

You can provide credentials directly when creating an API client instance:

```python
from bbcli.core.api_client import BitbucketAPIClient

client = BitbucketAPIClient(
    username="your_username",
    password="your_app_password"
)
```

### 2. Environment Variables (Medium Priority)

Set the following environment variables:

```bash
export BBCLI_USERNAME="your_username"
export BBCLI_PASSWORD="your_app_password"
```

Then create the client without parameters:

```python
client = BitbucketAPIClient()
```

### 3. Stored Credentials (Lowest Priority)

Use the CLI to store credentials securely:

```bash
bbcli auth login
```

Credentials are stored in the system keyring (preferred) or encrypted local file (fallback).

## Priority Order

The client checks for credentials in this order:

1. **Constructor parameters** - Highest priority
2. **Environment variables** - Medium priority
3. **Stored credentials** - Lowest priority

If multiple sources are available, the higher priority source is used.

## Basic Authentication Implementation

### Automatic Header Generation

The client automatically generates the `Authorization: Basic <encoded-credentials>` header for all requests in the `_make_request` method:

```python
# In _make_request method, the client automatically:
credentials = self._get_credentials()
if credentials:
    username, password = credentials
    auth_header = self._create_basic_auth_header(username, password)
    request_headers["Authorization"] = auth_header
```

This ensures that every HTTP request includes the proper Basic Authentication header when credentials are available.

### Manual Header Creation

You can also create Basic Auth headers manually:

```python
client = BitbucketAPIClient()
header = client._create_basic_auth_header("username", "password")
# Returns: "Basic dXNlcm5hbWU6cGFzc3dvcmQ="
```

## Authentication Validation

### Check Credential Availability

```python
client = BitbucketAPIClient()

# Check if any credentials are available
if client.has_credentials():
    print("Credentials are available")
else:
    print("No credentials found")
```

### Get Authentication Header

```python
# Get the Basic Auth header value
auth_header = client.get_auth_header()
if auth_header:
    print(f"Auth header: {auth_header}")
else:
    print("No credentials available")
```

### Validate Credentials

```python
# Test credentials by making an API call
is_valid = client.validate_credentials()
if is_valid:
    print("Credentials are valid")
else:
    print("Credentials are invalid or unavailable")
```

## Enhanced Error Handling

The client provides specific error messages based on the credential source:

### No Credentials Found

```
AuthenticationError: No authentication credentials found.
Suggestion: Run 'bbcli auth login' to set up authentication
```

### Invalid Constructor Credentials

```
AuthenticationError: Authentication failed with provided credentials.
Suggestion: Check your username and password
```

### Invalid Environment Variables

```
AuthenticationError: Authentication failed with environment variable credentials.
Suggestion: Check BBCLI_USERNAME and BBCLI_PASSWORD environment variables
```

### Invalid Stored Credentials

```
AuthenticationError: Authentication failed with stored credentials.
Suggestion: Run 'bbcli auth login' to re-authenticate
```

## Usage Examples

### Example 1: Using Constructor Parameters

```python
from bbcli.core.api_client import BitbucketAPIClient

client = BitbucketAPIClient(
    username="myuser",
    password="myapppassword"
)

# Make authenticated requests
user_info = client.get("/user")
workspaces = client.get("/workspaces")
```

### Example 2: Using Environment Variables

```bash
export BBCLI_USERNAME="myuser"
export BBCLI_PASSWORD="myapppassword"
```

```python
from bbcli.core.api_client import BitbucketAPIClient

client = BitbucketAPIClient()
user_info = client.get("/user")
```

### Example 3: Using Stored Credentials

```bash
# First, store credentials
bbcli auth login
```

```python
from bbcli.core.api_client import BitbucketAPIClient

client = BitbucketAPIClient()
user_info = client.get("/user")
```

### Example 4: Credential Validation

```python
from bbcli.core.api_client import BitbucketAPIClient
from bbcli.core.exceptions import AuthenticationError

client = BitbucketAPIClient(username="user", password="pass")

try:
    if client.validate_credentials():
        user_info = client.test_authentication()
        print(f"Authenticated as: {user_info['username']}")
    else:
        print("Invalid credentials")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    print(f"Suggestion: {e.suggestion}")
```

## Security Considerations

1. **Constructor parameters**: Credentials are stored in memory only
2. **Environment variables**: Credentials are visible to the process and child processes
3. **Stored credentials**: Encrypted and stored securely using system keyring or encrypted file

For production use, prefer stored credentials or environment variables over constructor parameters.

## Testing

The authentication features are thoroughly tested. Run the tests with:

```bash
uv run pytest tests/test_api_client.py::TestBitbucketAPIClientAuthentication -v
```

## Demo Script

A demonstration script is available at `examples/authentication_demo.py`:

```bash
# Run with constructor parameters
python examples/authentication_demo.py --username myuser --password mypass

# Run with environment variables
export BBCLI_USERNAME=myuser
export BBCLI_PASSWORD=mypass
python examples/authentication_demo.py

# Run without API calls (for testing)
python examples/authentication_demo.py --skip-api-calls
```
