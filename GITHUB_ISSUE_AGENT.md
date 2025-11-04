# GitHub Issue Agent

A comprehensive Python CLI tool for managing GitHub issues in the forgotten-depths repository. Create, list, query, update, comment on, and close issues directly from the command line.

## Features

- **Create** new issues with title, body, labels, assignees
- **List** issues with filtering by state, labels, assignee, creator
- **Get** detailed issue information including comments
- **Search** issues using GitHub's search syntax
- **Update** issue titles, bodies, labels, assignees
- **Comment** on existing issues
- **Close** and **reopen** issues
- **Manage labels** (add, remove, or set)
- **Query** available labels and milestones

## Setup

### 1. Install Dependencies

The agent uses the `requests` library, which should already be installed. If not:

```bash
pip install requests
```

### 2. Create a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens/new?scopes=repo
2. Give it a descriptive name like "Forgotten Depths Issue Agent"
3. Select the `repo` scope (this gives full access to private repositories)
4. Click "Generate token"
5. Copy the token (you won't be able to see it again!)

### 3. Set Your GitHub Token

#### Option A: Environment Variable (Recommended)

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

Then reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

#### Option B: Pass as Command-Line Argument

```bash
python3 scripts/github_issue_agent.py --token "ghp_your_token_here" create --title "My Issue"
```

## Quick Start

```bash
# List all open issues
python3 scripts/github_issue_agent.py list

# Create a new issue
python3 scripts/github_issue_agent.py create --title "Fix combat bug" --body "Players take double damage"

# Get details of issue #123
python3 scripts/github_issue_agent.py get 123

# Add a comment to issue #123
python3 scripts/github_issue_agent.py comment 123 --body "Working on this now"

# Close an issue
python3 scripts/github_issue_agent.py close 123 --comment "Fixed in commit abc123"
```

## Commands

### `create` - Create a New Issue

```bash
python3 scripts/github_issue_agent.py create --title "Issue title" [OPTIONS]
```

**Options:**
- `--title TITLE` (required) - Issue title
- `--body TEXT` - Issue description
- `--body-file FILE` - Read issue body from file
- `--labels LABELS` - Comma-separated list of labels
- `--assignees USERS` - Comma-separated list of GitHub usernames
- `--milestone NUMBER` - Milestone number

**Examples:**

```bash
# Simple issue
python3 scripts/github_issue_agent.py create --title "Fix player respawn bug"

# Issue with body and labels
python3 scripts/github_issue_agent.py create \
  --title "Add spell cooldown system" \
  --body "Implement cooldowns to prevent spell spamming" \
  --labels "enhancement,magic"

# Issue from file
python3 scripts/github_issue_agent.py create \
  --title "Performance issues in combat" \
  --body-file bug_report.md \
  --labels "bug,performance"
```

### `list` - List Issues

```bash
python3 scripts/github_issue_agent.py list [OPTIONS]
```

**Options:**
- `--state {open,closed,all}` - Issue state (default: open)
- `--labels LABELS` - Filter by labels (comma-separated)
- `--assignee USER` - Filter by assignee username
- `--creator USER` - Filter by creator username
- `--limit N` - Maximum number of issues to return (default: 30)

**Examples:**

```bash
# List all open issues
python3 scripts/github_issue_agent.py list

# List closed issues
python3 scripts/github_issue_agent.py list --state closed

# List bugs
python3 scripts/github_issue_agent.py list --labels bug

# List issues assigned to you
python3 scripts/github_issue_agent.py list --assignee jeff-brown

# List all issues (open and closed)
python3 scripts/github_issue_agent.py list --state all --limit 50
```

### `get` - Get Issue Details

```bash
python3 scripts/github_issue_agent.py get ISSUE_NUMBER [OPTIONS]
```

**Options:**
- `--comments` - Include all comments

**Examples:**

```bash
# Get issue details
python3 scripts/github_issue_agent.py get 123

# Get issue with all comments
python3 scripts/github_issue_agent.py get 123 --comments
```

### `search` - Search Issues

```bash
python3 scripts/github_issue_agent.py search QUERY [OPTIONS]
```

**Options:**
- `--limit N` - Maximum number of results (default: 30)

**Examples:**

```bash
# Search for issues about spells
python3 scripts/github_issue_agent.py search "spell system"

# Search is automatically scoped to the repository
# You can use GitHub search syntax
python3 scripts/github_issue_agent.py search "is:open label:bug combat"
```

### `update` - Update an Issue

```bash
python3 scripts/github_issue_agent.py update ISSUE_NUMBER [OPTIONS]
```

**Options:**
- `--title TEXT` - New title
- `--body TEXT` - New body
- `--body-file FILE` - Read new body from file
- `--labels LABELS` - New labels (comma-separated, replaces existing)
- `--assignees USERS` - New assignees (comma-separated, replaces existing)
- `--milestone NUMBER` - New milestone number

**Examples:**

```bash
# Update title
python3 scripts/github_issue_agent.py update 123 --title "New title"

# Update body
python3 scripts/github_issue_agent.py update 123 --body "Updated description"

# Update multiple fields
python3 scripts/github_issue_agent.py update 123 \
  --title "Combat bug fixed" \
  --labels "bug,fixed" \
  --assignees "jeff-brown"
```

### `comment` - Add a Comment

```bash
python3 scripts/github_issue_agent.py comment ISSUE_NUMBER [OPTIONS]
```

**Options:**
- `--body TEXT` - Comment text
- `--body-file FILE` - Read comment from file

**Examples:**

```bash
# Add a comment
python3 scripts/github_issue_agent.py comment 123 --body "Working on this now"

# Add comment from file
python3 scripts/github_issue_agent.py comment 123 --body-file update.md
```

### `close` - Close an Issue

```bash
python3 scripts/github_issue_agent.py close ISSUE_NUMBER [OPTIONS]
```

**Options:**
- `--comment TEXT` - Optional closing comment

**Examples:**

```bash
# Close issue
python3 scripts/github_issue_agent.py close 123

# Close with comment
python3 scripts/github_issue_agent.py close 123 --comment "Fixed in commit abc123"
```

### `reopen` - Reopen a Closed Issue

```bash
python3 scripts/github_issue_agent.py reopen ISSUE_NUMBER [OPTIONS]
```

**Options:**
- `--comment TEXT` - Optional reopening comment

**Examples:**

```bash
# Reopen issue
python3 scripts/github_issue_agent.py reopen 123

# Reopen with comment
python3 scripts/github_issue_agent.py reopen 123 --comment "Bug still present"
```

### `label` - Manage Issue Labels

```bash
python3 scripts/github_issue_agent.py label ISSUE_NUMBER [OPTIONS]
```

**Options:**
- `--add LABELS` - Labels to add (comma-separated, keeps existing)
- `--remove LABEL` - Label to remove
- `--set LABELS` - Set labels (comma-separated, replaces all existing)

**Examples:**

```bash
# Add labels
python3 scripts/github_issue_agent.py label 123 --add bug,critical

# Remove a label
python3 scripts/github_issue_agent.py label 123 --remove wontfix

# Replace all labels
python3 scripts/github_issue_agent.py label 123 --set bug,high-priority,combat
```

### `list-labels` - List Available Labels

```bash
python3 scripts/github_issue_agent.py list-labels
```

Shows all labels available in the repository.

### `list-milestones` - List Available Milestones

```bash
python3 scripts/github_issue_agent.py list-milestones
```

Shows all milestones in the repository.

## Common Workflows

### Bug Triage Workflow

```bash
# List all open bugs
python3 scripts/github_issue_agent.py list --labels bug

# Get details of a specific bug
python3 scripts/github_issue_agent.py get 123 --comments

# Add a comment with investigation notes
python3 scripts/github_issue_agent.py comment 123 --body "Reproduced. Issue is in combat_system.py:line_456"

# Add labels to categorize
python3 scripts/github_issue_agent.py label 123 --add critical,combat

# Assign to yourself
python3 scripts/github_issue_agent.py update 123 --assignees jeff-brown
```

### Feature Development Workflow

```bash
# Create feature issue
python3 scripts/github_issue_agent.py create \
  --title "Add quest system" \
  --body-file feature_spec.md \
  --labels enhancement,feature

# Track progress with comments
python3 scripts/github_issue_agent.py comment 123 --body "Quest data models completed"

# Close when done
python3 scripts/github_issue_agent.py close 123 --comment "Implemented in PR #45"
```

### Issue Review Workflow

```bash
# List all issues needing review
python3 scripts/github_issue_agent.py list --labels needs-review

# Review each issue
python3 scripts/github_issue_agent.py get 123 --comments

# Update labels based on review
python3 scripts/github_issue_agent.py label 123 --remove needs-review --add approved
```

## Advanced Usage

### Using with Claude Code CLI

From within Claude Code conversations, you can run the agent directly:

```
User: List all open combat-related issues
Claude: [runs] python3 scripts/github_issue_agent.py list --labels combat

User: Get details on issue 123
Claude: [runs] python3 scripts/github_issue_agent.py get 123 --comments

User: Create an issue for the spell bug we just found
Claude: [runs] python3 scripts/github_issue_agent.py create --title "Spell mana cost calculation incorrect" --body "..." --labels bug,magic
```

### Template Files

Create reusable templates for common issue types:

**bug_template.md:**
```markdown
## Description
[Describe the bug]

## Steps to Reproduce
1.
2.
3.

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Python version:
- OS:

## Additional Context
[Any other information]
```

Use it:
```bash
python3 scripts/github_issue_agent.py create \
  --title "Combat damage calculation wrong" \
  --body-file bug_template.md \
  --labels bug
```

### Batch Operations

```bash
# Close multiple issues
for issue in 101 102 103; do
  python3 scripts/github_issue_agent.py close $issue --comment "Duplicate of #100"
done

# Add label to multiple issues
for issue in 50 51 52; do
  python3 scripts/github_issue_agent.py label $issue --add needs-testing
done
```

## Tips

1. **Use Labels Effectively**: Labels help organize issues. Check available labels with `list-labels`

2. **Link to Code**: In issue bodies and comments, reference specific files and lines:
   ```
   See src/server/game/combat/combat_system.py:456
   ```

3. **Markdown Support**: Issue bodies and comments support full GitHub-flavored markdown:
   - Code blocks with syntax highlighting
   - Task lists: `- [ ] Todo item`
   - Tables, links, images
   - @mentions of GitHub users

4. **Search Syntax**: The `search` command supports GitHub's full search syntax:
   - `is:open` or `is:closed`
   - `label:bug`
   - `author:username`
   - `created:>2024-01-01`

5. **Automation**: Combine with shell scripts for powerful automation

## Troubleshooting

### "GitHub token is required"

Make sure your `GITHUB_TOKEN` environment variable is set or pass `--token`.

### "Failed to create issue: 401"

Your token is invalid or expired. Create a new one at the setup link.

### "Failed to create issue: 404"

The repository doesn't exist or your token doesn't have access. Check `--owner` and `--repo`.

### "requests library is required"

Install it: `pip install requests`

### Rate Limiting

GitHub API has rate limits. If you hit them, wait an hour or authenticate (which gives higher limits - already done with token).

## Global Options

These options work with all commands:

- `--token TOKEN` - GitHub personal access token
- `--owner OWNER` - Repository owner (default: jeff-brown)
- `--repo REPO` - Repository name (default: forgotten-depths)

Example:
```bash
python3 scripts/github_issue_agent.py --owner myuser --repo myrepo list
```
