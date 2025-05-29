# Repository Management

This document describes the repository management commands available in bbcli, including creating repositories, managing users, and listing repositories.

## Repository Commands

### `bbcli repo list`

List repositories in a workspace with optional filtering and search capabilities.

#### Usage

```bash
bbcli repo list --workspace WORKSPACE [OPTIONS]
```

#### Required Parameters

- `--workspace`, `-w`: Workspace slug or UUID where repositories are located

#### Optional Parameters

- `--project`, `-p`: Filter repositories by project key
- `--query`, `-q`: Filter repositories by name (text search)

#### Output Formats

The command supports all global output formats:

- **Text (default)**: Rich table with repository information
- **JSON**: Structured JSON output with repository details
- **YAML**: YAML formatted output

#### Examples

**Basic listing:**
```bash
bbcli repo list --workspace myworkspace
```

**Filter by project:**
```bash
bbcli repo list --workspace myworkspace --project WEBAPP
```

**Search by name:**
```bash
bbcli repo list --workspace myworkspace --query "frontend"
```

**Combined filters:**
```bash
bbcli repo list --workspace myworkspace --project WEBAPP --query "react"
```

**JSON output:**
```bash
bbcli --output json repo list --workspace myworkspace
```

#### Output Information

The command displays the following information for each repository:

- **Name**: Repository name
- **Project**: Project key the repository belongs to
- **Description**: Repository description (truncated to 100 characters)
- **Updated**: Last updated date and time
- **Visibility**: Private or Public

For JSON/YAML output, additional fields are included:

- **Language**: Primary programming language
- **Size**: Repository size in bytes
- **Full Name**: Complete repository identifier (workspace/repo)
- **Clone URL**: HTTPS clone URL
- **Web URL**: Bitbucket web interface URL

#### Pagination

The command automatically handles pagination and fetches all repositories that match the specified criteria. For workspaces with many repositories, this may take some time.

#### Filtering

**Project Filtering:**
- Uses exact match on project key
- Case-sensitive
- Example: `--project WEBAPP` matches only repositories in project "WEBAPP"

**Name Filtering:**
- Uses text search (partial matching)
- Case-insensitive
- Example: `--query "web"` matches repositories with "web" anywhere in the name

**Combined Filtering:**
- When both filters are used, repositories must match both criteria
- Uses logical AND operation

#### Error Handling

Common errors and solutions:

**"Workspace not found"**
- Verify the workspace slug is correct
- Ensure you have access to the workspace
- Check your authentication credentials

**"No repositories found"**
- The workspace exists but contains no repositories matching your criteria
- Try removing filters to see all repositories
- Verify project key spelling if using project filter

**Authentication errors**
- Run `bbcli auth status` to check authentication
- Re-authenticate with `bbcli auth login` if needed

#### API Integration

The command uses the Bitbucket Cloud REST API:
- Endpoint: `GET /repositories/{workspace}`
- Supports query parameters for filtering
- Handles pagination automatically
- Sorts results by last updated date (newest first)

#### Performance Considerations

- Large workspaces may take time to fetch all repositories
- Filtering is done server-side for better performance
- Results are sorted by update date for relevance

---

## Repository Creation

### `bbcli repo create`

Create a new repository in a workspace and project.

#### Usage

```bash
bbcli repo create REPOSITORY_NAME --project PROJECT_KEY --workspace WORKSPACE [OPTIONS]
```

#### Required Parameters

- `REPOSITORY_NAME`: Name of the repository to create
- `--project`: Project key where the repository will be created
- `--workspace`: Workspace slug or UUID

#### Optional Parameters

- `--description`: Repository description
- `--private` / `--public`: Set repository visibility (default: private)
- `--mainbranch`: Name of the main branch (e.g., 'main', 'master')
- `--language`: Programming language for the repository
- `--fork-policy`: Fork policy (allow_forks, no_public_forks, no_forks)

#### Examples

```bash
# Basic repository creation
bbcli repo create my-app --project MYPROJ --workspace myworkspace

# Public repository with description
bbcli repo create web-frontend --project WEBAPP --description "Frontend application" --public --workspace myworkspace

# Repository with custom main branch
bbcli repo create api-service --project BACKEND --mainbranch main --language Python --workspace myworkspace
```

---

## User Management

### `bbcli repo user add`

Add a user to a repository with specified permissions.

#### Usage

```bash
bbcli repo user add REPOSITORY_NAME --project PROJECT_KEY --user USER --permission PERMISSION --workspace WORKSPACE
```

#### Parameters

- `REPOSITORY_NAME`: Name of the repository
- `--project`: Project key
- `--user`: User email or account ID
- `--permission`: Permission level (read, write, admin)
- `--workspace`: Workspace slug or UUID

#### Example

```bash
bbcli repo user add my-repo --project MYPROJ --user user@example.com --permission write --workspace myworkspace
```

### `bbcli repo user remove`

Remove a user from a repository.

#### Usage

```bash
bbcli repo user remove REPOSITORY_NAME --project PROJECT_KEY --user USER --workspace WORKSPACE
```

#### Example

```bash
bbcli repo user remove my-repo --project MYPROJ --user user@example.com --workspace myworkspace
```

---

## Authentication

All repository commands require authentication. Use one of the following methods:

**OAuth 2.0 (Recommended):**
```bash
bbcli auth login
```

**App Password:**
```bash
bbcli auth login-basic
```

Check authentication status:
```bash
bbcli auth status
```

---

## Best Practices

1. **Use descriptive repository names**: Follow naming conventions like `kebab-case`
2. **Organize with projects**: Group related repositories in projects
3. **Set appropriate visibility**: Use private repositories for sensitive code
4. **Regular cleanup**: Use `bbcli repo list` to review and clean up unused repositories
5. **Filter effectively**: Use project and query filters to find repositories quickly
6. **Monitor permissions**: Regularly review repository access using user management commands

---

## Troubleshooting

**Command not found:**
- Ensure bbcli is properly installed and in your PATH

**Permission denied:**
- Check your authentication with `bbcli auth status`
- Verify you have access to the specified workspace
- Ensure your user has appropriate permissions

**Slow performance:**
- Large workspaces may take time to list all repositories
- Use filters to narrow down results
- Consider using JSON output for programmatic processing

**API rate limits:**
- Bitbucket has API rate limits
- If you encounter rate limiting, wait and retry
- Consider using filters to reduce API calls
