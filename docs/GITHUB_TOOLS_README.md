# GitHub Issue Management Tools

This repository includes two tools for managing GitHub issues:

## 1. CLI Tool (`scripts/github_issue_agent.py`)

A command-line interface for managing GitHub issues from the terminal.

**Documentation**: [GITHUB_ISSUE_AGENT.md](GITHUB_ISSUE_AGENT.md)

**Quick Start**:
```bash
export GITHUB_TOKEN="ghp_your_token"
python3 scripts/github_issue_agent.py list
python3 scripts/github_issue_agent.py create --title "Bug fix" --labels "bug"
```

**Best for**:
- Manual issue management from terminal
- Scripting and automation
- Batch operations

## 2. MCP Server (`scripts/github_issue_mcp_server.py`)

An MCP (Model Context Protocol) server that integrates GitHub issues directly into Claude Code.

**Documentation**: [GITHUB_ISSUE_MCP_SERVER.md](GITHUB_ISSUE_MCP_SERVER.md)

**Quick Start**:
1. Install FastMCP: `pip3 install fastmcp requests`
2. Configure Claude Code (see [GITHUB_ISSUE_MCP_SERVER.md](GITHUB_ISSUE_MCP_SERVER.md#installation))
3. Restart Claude Code
4. Use natural language: "Create a GitHub issue for the spell bug"

**Best for**:
- Native integration with Claude Code
- Natural language interaction
- Real-time issue management during development

## Comparison

| Feature | CLI Tool | MCP Server |
|---------|----------|------------|
| **Interface** | Command line | Claude Code (natural language) |
| **Setup** | Simple (just set token) | Requires MCP configuration |
| **Python Version** | Any 3.x | 3.10+ required |
| **Dependencies** | `requests` only | `fastmcp`, `requests` |
| **Use Case** | Scripts, automation | Interactive development |
| **Performance** | New process per command | Persistent connection |

## Configuration Files

- `claude_mcp_config_example.json` - Example MCP server configuration for Claude Code

## Current GitHub Issues

You can view all issues at: https://github.com/jeff-brown/forgotten-depths/issues

Currently tracked issues:
- #2: Cannot buy novadimaru due to partial matching bug
- #3: Spell fatigue not applying - spam casting exploit
- #4: Hunger/thirst not causing damage

## Environment Variables

Both tools require the same GitHub token:

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

To make persistent, add to `~/.zshrc` or `~/.bashrc`:

```bash
echo 'export GITHUB_TOKEN="ghp_your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

## Getting a GitHub Token

1. Go to https://github.com/settings/tokens/new?scopes=repo
2. Give it a name like "Forgotten Depths Issue Tools"
3. Select the `repo` scope
4. Click "Generate token"
5. Copy and save the token (you won't see it again!)

## Which Tool Should I Use?

**Use the CLI tool if you want to**:
- Run scripts or automation
- Work from the terminal
- Batch process multiple issues
- Use in CI/CD pipelines

**Use the MCP server if you want to**:
- Manage issues while coding in Claude Code
- Use natural language commands
- Have seamless integration
- Avoid switching between terminal and IDE

**Use both!** They work with the same repository and can be used interchangeably.
