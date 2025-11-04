#!/usr/bin/env python3
"""
GitHub Issues MCP Server using FastMCP.

Provides tools for managing GitHub issues directly from Claude Code.
"""

import os
from typing import Optional, List
import requests
from fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("GitHub Issues")

# GitHub configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER = "jeff-brown"
REPO = "forgotten-depths"
API_BASE = "https://api.github.com"


def get_headers():
    """Get headers for GitHub API requests."""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }


def format_issue_summary(issue: dict) -> str:
    """Format an issue for summary display."""
    labels = ", ".join([l["name"] for l in issue.get("labels", [])])
    assignees = ", ".join([a["login"] for a in issue.get("assignees", [])])

    parts = [
        f"#{issue['number']}: {issue['title']}",
        f"  State: {issue['state']}",
        f"  Created: {issue['created_at'][:10]} by {issue['user']['login']}",
    ]

    if labels:
        parts.append(f"  Labels: {labels}")
    if assignees:
        parts.append(f"  Assignees: {assignees}")
    if issue.get('comments', 0) > 0:
        parts.append(f"  Comments: {issue['comments']}")

    parts.append(f"  URL: {issue['html_url']}")

    return "\n".join(parts)


def format_issue_detail(issue: dict, comments: Optional[List[dict]] = None) -> str:
    """Format an issue for detailed display."""
    labels = ", ".join([l["name"] for l in issue.get("labels", [])])
    assignees = ", ".join([a["login"] for a in issue.get("assignees", [])])

    output = []
    output.append("=" * 80)
    output.append(f"Issue #{issue['number']}: {issue['title']}")
    output.append("=" * 80)
    output.append(f"State: {issue['state']}")
    output.append(f"Created: {issue['created_at']} by {issue['user']['login']}")
    output.append(f"Updated: {issue['updated_at']}")

    if labels:
        output.append(f"Labels: {labels}")
    if assignees:
        output.append(f"Assignees: {assignees}")
    if issue.get('milestone'):
        output.append(f"Milestone: {issue['milestone']['title']}")

    output.append(f"\nURL: {issue['html_url']}")
    output.append("\n" + "-" * 80)
    output.append("Description:")
    output.append("-" * 80)
    output.append(issue.get('body') or "(No description)")

    if comments:
        output.append("\n" + "-" * 80)
        output.append(f"Comments ({len(comments)}):")
        output.append("-" * 80)
        for i, comment in enumerate(comments, 1):
            output.append(f"\n[Comment #{i}] {comment['user']['login']} on {comment['created_at'][:10]}:")
            output.append(comment['body'])
            output.append("")

    output.append("=" * 80)

    return "\n".join(output)


@mcp.tool()
def create_issue(
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None
) -> str:
    """
    Create a new GitHub issue.

    Args:
        title: Issue title (required)
        body: Issue description (supports markdown)
        labels: List of label names to apply
        assignees: List of GitHub usernames to assign

    Returns:
        Success message with issue number and URL
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues"

    data = {"title": title}
    if body:
        data["body"] = body
    if labels:
        data["labels"] = labels
    if assignees:
        data["assignees"] = assignees

    response = requests.post(url, headers=get_headers(), json=data)

    if response.status_code == 201:
        issue = response.json()
        return f"✅ Issue #{issue['number']} created successfully!\nURL: {issue['html_url']}"
    else:
        raise Exception(f"Failed to create issue: {response.status_code} - {response.text}")


@mcp.tool()
def list_issues(
    state: str = "open",
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    limit: int = 30
) -> str:
    """
    List issues in the repository with optional filtering.

    Args:
        state: Issue state - "open", "closed", or "all" (default: "open")
        labels: Filter by these labels
        assignee: Filter by assignee username
        limit: Maximum number of issues to return (default: 30)

    Returns:
        Formatted list of issues
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues"

    params = {"state": state, "per_page": limit}
    if labels:
        params["labels"] = ",".join(labels)
    if assignee:
        params["assignee"] = assignee

    response = requests.get(url, headers=get_headers(), params=params)

    if response.status_code == 200:
        issues = response.json()
        if not issues:
            return f"No {state} issues found."

        result = f"Found {len(issues)} {state} issue(s):\n\n"
        for issue in issues:
            result += format_issue_summary(issue) + "\n\n"
        return result
    else:
        raise Exception(f"Failed to list issues: {response.status_code} - {response.text}")


@mcp.tool()
def get_issue(issue_number: int, include_comments: bool = False) -> str:
    """
    Get detailed information about a specific issue.

    Args:
        issue_number: Issue number
        include_comments: Include comments in the response (default: False)

    Returns:
        Detailed issue information
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues/{issue_number}"
    response = requests.get(url, headers=get_headers())

    if response.status_code != 200:
        raise Exception(f"Failed to get issue: {response.status_code} - {response.text}")

    issue = response.json()
    comments = None

    if include_comments:
        comments_url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues/{issue_number}/comments"
        comments_response = requests.get(comments_url, headers=get_headers())
        if comments_response.status_code == 200:
            comments = comments_response.json()

    return format_issue_detail(issue, comments)


@mcp.tool()
def add_comment(issue_number: int, comment: str) -> str:
    """
    Add a comment to an issue.

    Args:
        issue_number: Issue number
        comment: Comment text (supports markdown)

    Returns:
        Success message with comment URL
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues/{issue_number}/comments"
    data = {"body": comment}

    response = requests.post(url, headers=get_headers(), json=data)

    if response.status_code == 201:
        result = response.json()
        return f"✅ Comment added to issue #{issue_number}\nURL: {result['html_url']}"
    else:
        raise Exception(f"Failed to add comment: {response.status_code} - {response.text}")


@mcp.tool()
def update_issue(
    issue_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None
) -> str:
    """
    Update an existing issue.

    Args:
        issue_number: Issue number
        title: New title
        body: New body
        state: New state ("open" or "closed")
        labels: New labels (replaces existing)
        assignees: New assignees (replaces existing)

    Returns:
        Success message with issue URL
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues/{issue_number}"

    data = {}
    if title is not None:
        data["title"] = title
    if body is not None:
        data["body"] = body
    if state is not None:
        data["state"] = state
    if labels is not None:
        data["labels"] = labels
    if assignees is not None:
        data["assignees"] = assignees

    response = requests.patch(url, headers=get_headers(), json=data)

    if response.status_code == 200:
        issue = response.json()
        return f"✅ Issue #{issue['number']} updated successfully!\nURL: {issue['html_url']}"
    else:
        raise Exception(f"Failed to update issue: {response.status_code} - {response.text}")


@mcp.tool()
def close_issue(issue_number: int, comment: Optional[str] = None) -> str:
    """
    Close an issue with an optional closing comment.

    Args:
        issue_number: Issue number
        comment: Optional closing comment

    Returns:
        Success message
    """
    if comment:
        add_comment(issue_number, comment)

    return update_issue(issue_number, state="closed")


@mcp.tool()
def reopen_issue(issue_number: int, comment: Optional[str] = None) -> str:
    """
    Reopen a closed issue with an optional comment.

    Args:
        issue_number: Issue number
        comment: Optional reopening comment

    Returns:
        Success message
    """
    if comment:
        add_comment(issue_number, comment)

    return update_issue(issue_number, state="open")


@mcp.tool()
def add_labels(issue_number: int, labels: List[str]) -> str:
    """
    Add labels to an issue (keeps existing labels).

    Args:
        issue_number: Issue number
        labels: Labels to add

    Returns:
        Success message
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues/{issue_number}/labels"
    data = {"labels": labels}

    response = requests.post(url, headers=get_headers(), json=data)

    if response.status_code == 200:
        return f"✅ Added labels to issue #{issue_number}: {', '.join(labels)}"
    else:
        raise Exception(f"Failed to add labels: {response.status_code} - {response.text}")


@mcp.tool()
def remove_label(issue_number: int, label: str) -> str:
    """
    Remove a label from an issue.

    Args:
        issue_number: Issue number
        label: Label to remove

    Returns:
        Success message
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/issues/{issue_number}/labels/{label}"
    response = requests.delete(url, headers=get_headers())

    if response.status_code in [200, 204]:
        return f"✅ Removed label '{label}' from issue #{issue_number}"
    else:
        raise Exception(f"Failed to remove label: {response.status_code} - {response.text}")


@mcp.tool()
def search_issues(query: str, limit: int = 30) -> str:
    """
    Search issues using GitHub's search syntax.

    Args:
        query: Search query (automatically scoped to repository)
        limit: Maximum number of results (default: 30)

    Returns:
        Formatted list of matching issues

    Examples:
        - "spell system" - Search for these words
        - "is:open label:bug" - Open bugs
        - "author:username" - Issues by author
    """
    full_query = f"{query} repo:{OWNER}/{REPO}"
    url = f"{API_BASE}/search/issues"
    params = {"q": full_query, "per_page": limit}

    response = requests.get(url, headers=get_headers(), params=params)

    if response.status_code == 200:
        issues = response.json()["items"]
        if not issues:
            return f"No issues found matching '{query}'."

        result = f"Found {len(issues)} issue(s) matching '{query}':\n\n"
        for issue in issues:
            result += format_issue_summary(issue) + "\n\n"
        return result
    else:
        raise Exception(f"Failed to search issues: {response.status_code} - {response.text}")


@mcp.tool()
def list_labels() -> str:
    """
    List all available labels in the repository.

    Returns:
        Formatted list of labels
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/labels"
    response = requests.get(url, headers=get_headers())

    if response.status_code == 200:
        labels = response.json()
        result = f"Available labels ({len(labels)}):\n\n"
        for label in labels:
            desc = f" - {label['description']}" if label['description'] else ""
            result += f"  • {label['name']}{desc}\n"
        return result
    else:
        raise Exception(f"Failed to list labels: {response.status_code} - {response.text}")


@mcp.tool()
def list_milestones() -> str:
    """
    List all milestones in the repository.

    Returns:
        Formatted list of milestones
    """
    url = f"{API_BASE}/repos/{OWNER}/{REPO}/milestones"
    response = requests.get(url, headers=get_headers())

    if response.status_code == 200:
        milestones = response.json()
        if not milestones:
            return "No milestones found in the repository."

        result = f"Available milestones ({len(milestones)}):\n\n"
        for milestone in milestones:
            result += f"  • {milestone['number']}. {milestone['title']} - {milestone['state']}\n"
            if milestone['description']:
                result += f"    {milestone['description']}\n"
        return result
    else:
        raise Exception(f"Failed to list milestones: {response.status_code} - {response.text}")


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
