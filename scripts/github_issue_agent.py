#!/usr/bin/env python3
"""
GitHub Issue Agent for Forgotten Depths MUD.

This script allows you to create, query, and modify GitHub issues in the
forgotten-depths repository using the GitHub API. It supports both interactive
and command-line modes.
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)


class GitHubIssueAgent:
    """Agent for managing GitHub issues."""

    def __init__(self, token: Optional[str] = None, owner: str = "jeff-brown", repo: str = "forgotten-depths"):
        """
        Initialize the GitHub Issue Agent.

        Args:
            token: GitHub personal access token (if None, reads from GITHUB_TOKEN env var)
            owner: Repository owner
            repo: Repository name
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.owner = owner
        self.repo = repo
        self.api_base = "https://api.github.com"

        if not self.token:
            raise ValueError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable or pass it as --token.\n"
                "Create a token at: https://github.com/settings/tokens/new?scopes=repo"
            )

    @property
    def headers(self):
        """Get headers for API requests."""
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

    def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> dict:
        """
        Create a new GitHub issue.

        Args:
            title: Issue title
            body: Issue body/description
            labels: List of label names
            assignees: List of GitHub usernames to assign
            milestone: Milestone number

        Returns:
            dict: GitHub API response with issue details
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues"

        data = {
            "title": title,
        }

        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        if milestone:
            data["milestone"] = milestone

        response = requests.post(url, headers=self.headers, json=data)

        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create issue: {response.status_code} - {response.text}")

    def list_labels(self) -> List[dict]:
        """Get list of available labels in the repository."""
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/labels"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list labels: {response.status_code} - {response.text}")

    def list_milestones(self) -> List[dict]:
        """Get list of available milestones in the repository."""
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/milestones"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list milestones: {response.status_code} - {response.text}")

    def list_issues(
        self,
        state: str = "open",
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        creator: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 30
    ) -> List[dict]:
        """
        List issues in the repository.

        Args:
            state: Issue state ('open', 'closed', 'all')
            labels: Filter by labels
            assignee: Filter by assignee username
            creator: Filter by creator username
            since: Only issues updated after this date (ISO 8601 format)
            limit: Maximum number of issues to return

        Returns:
            List of issue dictionaries
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues"

        params = {
            "state": state,
            "per_page": limit
        }

        if labels:
            params["labels"] = ",".join(labels)
        if assignee:
            params["assignee"] = assignee
        if creator:
            params["creator"] = creator
        if since:
            params["since"] = since

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list issues: {response.status_code} - {response.text}")

    def get_issue(self, issue_number: int) -> dict:
        """
        Get a specific issue by number.

        Args:
            issue_number: Issue number

        Returns:
            Issue dictionary
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{issue_number}"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get issue: {response.status_code} - {response.text}")

    def update_issue(
        self,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> dict:
        """
        Update an existing issue.

        Args:
            issue_number: Issue number to update
            title: New title
            body: New body
            state: New state ('open' or 'closed')
            labels: New labels (replaces existing)
            assignees: New assignees (replaces existing)
            milestone: New milestone number

        Returns:
            Updated issue dictionary
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{issue_number}"

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
        if milestone is not None:
            data["milestone"] = milestone

        response = requests.patch(url, headers=self.headers, json=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to update issue: {response.status_code} - {response.text}")

    def add_comment(self, issue_number: int, comment: str) -> dict:
        """
        Add a comment to an issue.

        Args:
            issue_number: Issue number
            comment: Comment text

        Returns:
            Comment dictionary
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments"
        data = {"body": comment}

        response = requests.post(url, headers=self.headers, json=data)

        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to add comment: {response.status_code} - {response.text}")

    def get_comments(self, issue_number: int) -> List[dict]:
        """
        Get comments for an issue.

        Args:
            issue_number: Issue number

        Returns:
            List of comment dictionaries
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get comments: {response.status_code} - {response.text}")

    def close_issue(self, issue_number: int, comment: Optional[str] = None) -> dict:
        """
        Close an issue.

        Args:
            issue_number: Issue number
            comment: Optional closing comment

        Returns:
            Updated issue dictionary
        """
        if comment:
            self.add_comment(issue_number, comment)

        return self.update_issue(issue_number, state="closed")

    def reopen_issue(self, issue_number: int, comment: Optional[str] = None) -> dict:
        """
        Reopen a closed issue.

        Args:
            issue_number: Issue number
            comment: Optional reopening comment

        Returns:
            Updated issue dictionary
        """
        if comment:
            self.add_comment(issue_number, comment)

        return self.update_issue(issue_number, state="open")

    def add_labels(self, issue_number: int, labels: List[str]) -> List[dict]:
        """
        Add labels to an issue (without removing existing ones).

        Args:
            issue_number: Issue number
            labels: Labels to add

        Returns:
            Updated list of labels
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{issue_number}/labels"
        data = {"labels": labels}

        response = requests.post(url, headers=self.headers, json=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to add labels: {response.status_code} - {response.text}")

    def remove_label(self, issue_number: int, label: str) -> None:
        """
        Remove a label from an issue.

        Args:
            issue_number: Issue number
            label: Label to remove
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{issue_number}/labels/{label}"
        response = requests.delete(url, headers=self.headers)

        if response.status_code not in [200, 204]:
            raise Exception(f"Failed to remove label: {response.status_code} - {response.text}")

    def search_issues(self, query: str, limit: int = 30) -> List[dict]:
        """
        Search issues using GitHub's search syntax.

        Args:
            query: Search query (will be scoped to this repo)
            limit: Maximum number of results

        Returns:
            List of matching issues
        """
        # Scope the search to this repository
        full_query = f"{query} repo:{self.owner}/{self.repo}"

        url = f"{self.api_base}/search/issues"
        params = {
            "q": full_query,
            "per_page": limit
        }

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()["items"]
        else:
            raise Exception(f"Failed to search issues: {response.status_code} - {response.text}")


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


def format_issue_detail(issue: dict, include_comments: bool = False, comments: Optional[List[dict]] = None) -> str:
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

    if include_comments and comments:
        output.append("\n" + "-" * 80)
        output.append(f"Comments ({len(comments)}):")
        output.append("-" * 80)
        for i, comment in enumerate(comments, 1):
            output.append(f"\n[Comment #{i}] {comment['user']['login']} on {comment['created_at'][:10]}:")
            output.append(comment['body'])
            output.append("")

    output.append("=" * 80)

    return "\n".join(output)


def interactive_mode(agent: GitHubIssueAgent):
    """Run the agent in interactive mode."""
    print("=== GitHub Issue Agent - Interactive Mode ===")
    print()

    # Get title
    title = input("Issue title: ").strip()
    if not title:
        print("Error: Title is required.")
        return

    # Get body
    print("\nIssue body (press Ctrl+D or Ctrl+Z when done, or leave empty):")
    body_lines = []
    try:
        while True:
            line = input()
            body_lines.append(line)
    except EOFError:
        pass
    body = "\n".join(body_lines).strip() or None

    # Get labels
    print("\nAvailable labels:")
    try:
        labels = agent.list_labels()
        for i, label in enumerate(labels[:20], 1):  # Show first 20 labels
            print(f"  {i}. {label['name']} - {label['description'] or 'No description'}")
        if len(labels) > 20:
            print(f"  ... and {len(labels) - 20} more")
    except Exception as e:
        print(f"Could not fetch labels: {e}")
        labels = []

    label_input = input("\nLabel names (comma-separated, or leave empty): ").strip()
    selected_labels = [l.strip() for l in label_input.split(",")] if label_input else None

    # Get assignees
    assignee_input = input("\nAssignees (comma-separated GitHub usernames, or leave empty): ").strip()
    assignees = [a.strip() for a in assignee_input.split(",")] if assignee_input else None

    # Create issue
    print("\nCreating issue...")
    try:
        issue = agent.create_issue(
            title=title,
            body=body,
            labels=selected_labels,
            assignees=assignees
        )
        print(f"\nSuccess! Issue created:")
        print(f"  Number: #{issue['number']}")
        print(f"  URL: {issue['html_url']}")
        print(f"  State: {issue['state']}")
    except Exception as e:
        print(f"\nError creating issue: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="GitHub Issue Agent for Forgotten Depths MUD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create issue
  python3 scripts/github_issue_agent.py create --title "Fix bug" --body "Description"

  # List open issues
  python3 scripts/github_issue_agent.py list

  # List closed issues
  python3 scripts/github_issue_agent.py list --state closed

  # Get issue details
  python3 scripts/github_issue_agent.py get 123

  # Get issue with comments
  python3 scripts/github_issue_agent.py get 123 --comments

  # Search issues
  python3 scripts/github_issue_agent.py search "spell system"

  # Update issue
  python3 scripts/github_issue_agent.py update 123 --title "New title"

  # Add comment
  python3 scripts/github_issue_agent.py comment 123 --body "Great idea!"

  # Close issue
  python3 scripts/github_issue_agent.py close 123 --comment "Fixed in commit abc123"

  # Reopen issue
  python3 scripts/github_issue_agent.py reopen 123

  # Add labels
  python3 scripts/github_issue_agent.py label 123 --add bug,critical

  # Remove label
  python3 scripts/github_issue_agent.py label 123 --remove wontfix

Environment:
  GITHUB_TOKEN - GitHub personal access token (required)
                 Create at: https://github.com/settings/tokens/new?scopes=repo
        """
    )

    parser.add_argument("--token", help="GitHub personal access token (or set GITHUB_TOKEN env var)")
    parser.add_argument("--owner", default="jeff-brown", help="Repository owner (default: jeff-brown)")
    parser.add_argument("--repo", default="forgotten-depths", help="Repository name (default: forgotten-depths)")

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new issue')
    create_parser.add_argument('--title', required=True, help='Issue title')
    create_parser.add_argument('--body', help='Issue body/description')
    create_parser.add_argument('--body-file', help='Read issue body from file')
    create_parser.add_argument('--labels', help='Comma-separated list of labels')
    create_parser.add_argument('--assignees', help='Comma-separated list of GitHub usernames')
    create_parser.add_argument('--milestone', type=int, help='Milestone number')

    # List command
    list_parser = subparsers.add_parser('list', help='List issues')
    list_parser.add_argument('--state', default='open', choices=['open', 'closed', 'all'], help='Issue state')
    list_parser.add_argument('--labels', help='Filter by labels (comma-separated)')
    list_parser.add_argument('--assignee', help='Filter by assignee username')
    list_parser.add_argument('--creator', help='Filter by creator username')
    list_parser.add_argument('--limit', type=int, default=30, help='Maximum number of issues to return')

    # Get command
    get_parser = subparsers.add_parser('get', help='Get issue details')
    get_parser.add_argument('issue_number', type=int, help='Issue number')
    get_parser.add_argument('--comments', action='store_true', help='Include comments')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search issues')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=30, help='Maximum number of results')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update an issue')
    update_parser.add_argument('issue_number', type=int, help='Issue number')
    update_parser.add_argument('--title', help='New title')
    update_parser.add_argument('--body', help='New body')
    update_parser.add_argument('--body-file', help='Read new body from file')
    update_parser.add_argument('--labels', help='New labels (comma-separated, replaces existing)')
    update_parser.add_argument('--assignees', help='New assignees (comma-separated, replaces existing)')
    update_parser.add_argument('--milestone', type=int, help='New milestone number')

    # Comment command
    comment_parser = subparsers.add_parser('comment', help='Add a comment to an issue')
    comment_parser.add_argument('issue_number', type=int, help='Issue number')
    comment_parser.add_argument('--body', help='Comment text')
    comment_parser.add_argument('--body-file', help='Read comment from file')

    # Close command
    close_parser = subparsers.add_parser('close', help='Close an issue')
    close_parser.add_argument('issue_number', type=int, help='Issue number')
    close_parser.add_argument('--comment', help='Optional closing comment')

    # Reopen command
    reopen_parser = subparsers.add_parser('reopen', help='Reopen a closed issue')
    reopen_parser.add_argument('issue_number', type=int, help='Issue number')
    reopen_parser.add_argument('--comment', help='Optional reopening comment')

    # Label command
    label_parser = subparsers.add_parser('label', help='Manage issue labels')
    label_parser.add_argument('issue_number', type=int, help='Issue number')
    label_parser.add_argument('--add', help='Labels to add (comma-separated)')
    label_parser.add_argument('--remove', help='Label to remove')
    label_parser.add_argument('--set', help='Set labels (comma-separated, replaces existing)')

    # Info commands
    subparsers.add_parser('list-labels', help='List available labels')
    subparsers.add_parser('list-milestones', help='List available milestones')

    args = parser.parse_args()

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Initialize agent
    try:
        agent = GitHubIssueAgent(token=args.token, owner=args.owner, repo=args.repo)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        # Handle commands
        if args.command == 'create':
            # Read body from file if specified
            body = args.body
            if args.body_file:
                with open(args.body_file, 'r') as f:
                    body = f.read()

            labels = [l.strip() for l in args.labels.split(",")] if args.labels else None
            assignees = [a.strip() for a in args.assignees.split(",")] if args.assignees else None

            issue = agent.create_issue(
                title=args.title,
                body=body,
                labels=labels,
                assignees=assignees,
                milestone=args.milestone
            )
            print(f"Success! Issue #{issue['number']} created:")
            print(f"  URL: {issue['html_url']}")

        elif args.command == 'list':
            labels = [l.strip() for l in args.labels.split(",")] if args.labels else None

            issues = agent.list_issues(
                state=args.state,
                labels=labels,
                assignee=args.assignee,
                creator=args.creator,
                limit=args.limit
            )

            if not issues:
                print(f"No {args.state} issues found.")
            else:
                print(f"Found {len(issues)} {args.state} issue(s):\n")
                for issue in issues:
                    print(format_issue_summary(issue))
                    print()

        elif args.command == 'get':
            issue = agent.get_issue(args.issue_number)
            comments = None

            if args.comments:
                comments = agent.get_comments(args.issue_number)

            print(format_issue_detail(issue, include_comments=args.comments, comments=comments))

        elif args.command == 'search':
            issues = agent.search_issues(args.query, limit=args.limit)

            if not issues:
                print(f"No issues found matching '{args.query}'.")
            else:
                print(f"Found {len(issues)} issue(s) matching '{args.query}':\n")
                for issue in issues:
                    print(format_issue_summary(issue))
                    print()

        elif args.command == 'update':
            # Read body from file if specified
            body = args.body
            if args.body_file:
                with open(args.body_file, 'r') as f:
                    body = f.read()

            labels = [l.strip() for l in args.labels.split(",")] if args.labels else None
            assignees = [a.strip() for a in args.assignees.split(",")] if args.assignees else None

            issue = agent.update_issue(
                issue_number=args.issue_number,
                title=args.title,
                body=body,
                labels=labels,
                assignees=assignees,
                milestone=args.milestone
            )
            print(f"Success! Issue #{issue['number']} updated:")
            print(f"  URL: {issue['html_url']}")

        elif args.command == 'comment':
            # Read body from file if specified
            body = args.body
            if args.body_file:
                with open(args.body_file, 'r') as f:
                    body = f.read()

            if not body:
                print("Error: Comment body is required (--body or --body-file)")
                sys.exit(1)

            comment = agent.add_comment(args.issue_number, body)
            print(f"Success! Comment added to issue #{args.issue_number}")
            print(f"  URL: {comment['html_url']}")

        elif args.command == 'close':
            issue = agent.close_issue(args.issue_number, comment=args.comment)
            print(f"Success! Issue #{issue['number']} closed:")
            print(f"  URL: {issue['html_url']}")

        elif args.command == 'reopen':
            issue = agent.reopen_issue(args.issue_number, comment=args.comment)
            print(f"Success! Issue #{issue['number']} reopened:")
            print(f"  URL: {issue['html_url']}")

        elif args.command == 'label':
            if args.add:
                labels = [l.strip() for l in args.add.split(",")]
                agent.add_labels(args.issue_number, labels)
                print(f"Success! Added labels to issue #{args.issue_number}: {', '.join(labels)}")

            elif args.remove:
                agent.remove_label(args.issue_number, args.remove)
                print(f"Success! Removed label '{args.remove}' from issue #{args.issue_number}")

            elif args.set:
                labels = [l.strip() for l in args.set.split(",")]
                agent.update_issue(args.issue_number, labels=labels)
                print(f"Success! Set labels for issue #{args.issue_number}: {', '.join(labels)}")

            else:
                print("Error: Specify --add, --remove, or --set")
                sys.exit(1)

        elif args.command == 'list-labels':
            labels = agent.list_labels()
            print(f"Available labels in {args.owner}/{args.repo}:")
            for label in labels:
                desc = f" - {label['description']}" if label['description'] else ""
                print(f"  {label['name']}{desc}")
            print(f"\nTotal: {len(labels)} labels")

        elif args.command == 'list-milestones':
            milestones = agent.list_milestones()
            print(f"Available milestones in {args.owner}/{args.repo}:")
            for milestone in milestones:
                print(f"  {milestone['number']}. {milestone['title']} - {milestone['state']}")
                if milestone['description']:
                    print(f"     {milestone['description']}")
            print(f"\nTotal: {len(milestones)} milestones")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
