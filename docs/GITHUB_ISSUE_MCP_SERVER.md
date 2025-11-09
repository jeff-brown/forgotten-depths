# GitHub Issues MCP Server

An MCP (Model Context Protocol) server that provides GitHub issue management capabilities directly to Claude Code and other MCP clients.

## Features

The MCP server provides the following tools:

- **create_issue** - Create new issues with title, body, labels, and assignees
- **list_issues** - List issues with filtering by state, labels, assignee
- **get_issue** - Get detailed issue information with optional comments
- **update_issue** - Update issue title, body, labels, assignees, or state
- **add_comment** - Add comments to issues
- **close_issue** - Close issues with optional closing comment
- **reopen_issue** - Reopen closed issues with optional comment
- **add_labels** - Add labels to an issue (keeps existing)
- **remove_label** - Remove a specific label from an issue
- **search_issues** - Search issues using GitHub's search syntax
- **list_labels** - List all available repository labels
- **list_milestones** - List all repository milestones

## Installation

### 1. Install Required Dependencies

The MCP server requires Python 3.10+ and the `fastmcp` and `requests` packages.

**Note**: If your system Python is older than 3.10, you'll need to install Python 3.10 or later first.

```bash
# Using the system Python 3 (must be 3.10+)
pip3 install fastmcp requests

# Or if you installed Python 3.14 specifically:
/usr/local/bin/python3 -m pip install fastmcp requests
```

### 2. Set Up GitHub Token

Set your GitHub personal access token as an environment variable:

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

To make this persistent, add it to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
echo 'export GITHUB_TOKEN="ghp_your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Configure Claude Code to Use the MCP Server

Add the MCP server to your Claude Code configuration. The configuration file is typically located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following to the `mcpServers` section:

```json
{
  "mcpServers": {
    "github-issues": {
      "command": "/usr/local/bin/python3",
      "args": [
        "/Users/jeffreybrown/git/jeff-brown/forgotten-depths/scripts/github_issue_mcp_server.py"
      ],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

**Note**:
- Update the path to the script to match your actual installation location
- Update the `command` to point to your Python 3.10+ installation (use `/usr/local/bin/python3`, `/opt/homebrew/bin/python3`, or `python3` depending on your setup)

### 4. Restart Claude Code

After adding the configuration, restart Claude Code for the changes to take effect.

## Usage

Once configured, Claude Code will automatically have access to the GitHub issue management tools. You can interact with GitHub issues naturally in conversation.

### Examples

**Create an issue:**
```
Create a GitHub issue titled "Fix combat bug" with the label "bug"
```

**List open issues:**
```
List all open GitHub issues
```

**Get issue details:**
```
Show me the details of GitHub issue #5
```

**Add a comment:**
```
Add a comment to issue #5 saying "I'm working on this"
```

**Close an issue:**
```
Close GitHub issue #5 with a comment "Fixed in latest commit"
```

**Search issues:**
```
Search for GitHub issues related to "spell system"
```

**List labels:**
```
What labels are available in the repository?
```

## Tool Reference

### github_create_issue

Create a new GitHub issue.

**Parameters:**
- `title` (required): Issue title
- `body` (optional): Issue description (supports Markdown)
- `labels` (optional): Array of label names
- `assignees` (optional): Array of GitHub usernames

**Example:**
```json
{
  "title": "Fix combat damage calculation",
  "body": "The combat system is calculating damage incorrectly...",
  "labels": ["bug", "combat"],
  "assignees": ["jeff-brown"]
}
```

### github_list_issues

List issues with optional filtering.

**Parameters:**
- `state` (optional): "open", "closed", or "all" (default: "open")
- `labels` (optional): Array of labels to filter by
- `assignee` (optional): Filter by assignee username
- `limit` (optional): Maximum number of issues (default: 30)

### github_get_issue

Get detailed information about a specific issue.

**Parameters:**
- `issue_number` (required): Issue number
- `include_comments` (optional): Include comments (default: false)

### github_update_issue

Update an existing issue.

**Parameters:**
- `issue_number` (required): Issue number
- `title` (optional): New title
- `body` (optional): New body
- `state` (optional): "open" or "closed"
- `labels` (optional): New labels (replaces existing)
- `assignees` (optional): New assignees (replaces existing)

### github_add_comment

Add a comment to an issue.

**Parameters:**
- `issue_number` (required): Issue number
- `comment` (required): Comment text (supports Markdown)

### github_close_issue

Close an issue.

**Parameters:**
- `issue_number` (required): Issue number
- `comment` (optional): Closing comment

### github_reopen_issue

Reopen a closed issue.

**Parameters:**
- `issue_number` (required): Issue number
- `comment` (optional): Reopening comment

### github_add_labels

Add labels to an issue (keeps existing labels).

**Parameters:**
- `issue_number` (required): Issue number
- `labels` (required): Array of label names to add

### github_remove_label

Remove a label from an issue.

**Parameters:**
- `issue_number` (required): Issue number
- `label` (required): Label name to remove

### github_search_issues

Search issues using GitHub's search syntax.

**Parameters:**
- `query` (required): Search query (automatically scoped to repository)
- `limit` (optional): Maximum results (default: 30)

**Example queries:**
- `"spell system"` - Search for issues containing these words
- `"is:open label:bug"` - Open bugs
- `"author:jeff-brown"` - Issues created by a specific user

### github_list_labels

List all available labels in the repository.

**Parameters:** None

### github_list_milestones

List all milestones in the repository.

**Parameters:** None

## Advantages Over CLI Tool

The MCP server provides several advantages over the command-line tool:

1. **Native Integration**: Tools appear directly in Claude Code's tool palette
2. **No Shell Commands**: No need to construct bash commands with tokens
3. **Type Safety**: Parameters are validated automatically
4. **Better UX**: Results are formatted consistently
5. **Persistent Connection**: Faster than spawning new processes for each command
6. **Automatic Context**: Claude understands the tool capabilities automatically

## Customization

To use with a different repository, modify the `GitHubIssueAgent` initialization in the script:

```python
agent = GitHubIssueAgent(
    owner="your-username",
    repo="your-repo-name"
)
```

Or make these configurable via environment variables.

## Troubleshooting

### "GitHub token not configured"

Make sure the `GITHUB_TOKEN` environment variable is set in the MCP server configuration.

### "Module 'fastmcp' not found"

Install FastMCP:
```bash
pip3 install fastmcp

# Or with Python 3.14:
/usr/local/bin/python3 -m pip install fastmcp
```

### "Python version too old"

FastMCP requires Python 3.10 or later. Check your Python version:
```bash
python3 --version
```

If it's older than 3.10, you'll need to install a newer version of Python.

### Server not appearing in Claude Code

1. Verify the path in `claude_desktop_config.json` is correct
2. Check that the script has execute permissions: `chmod +x github_issue_mcp_server.py`
3. Restart Claude Code completely
4. Check the Claude Code logs for errors

### Permission Errors

Ensure your GitHub token has the `repo` scope enabled. Create a new token at:
https://github.com/settings/tokens/new?scopes=repo

## Development

To test the MCP server locally:

```bash
# Set your token
export GITHUB_TOKEN="ghp_your_token_here"

# Run the server (it will wait for MCP protocol messages on stdin)
python3 scripts/github_issue_mcp_server.py
```

For debugging, you can add logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Notes

- Keep your GitHub token secure and never commit it to version control
- The token should have minimal required permissions (typically just `repo`)
- Consider using environment-specific tokens for different projects
- Regularly rotate your tokens for security

## Related Documentation

- [Original CLI Tool Documentation](GITHUB_ISSUE_AGENT.md)
- [MCP Protocol Documentation](https://modelcontextprotocol.io)
- [GitHub API Documentation](https://docs.github.com/en/rest)
