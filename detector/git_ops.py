"""Git and GitHub operations for automated PR creation."""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict
from git import Repo
from github import Github, GithubException


def get_git_repo(path: Path) -> Optional[Repo]:
    """Get Git repository object from path."""
    try:
        return Repo(path, search_parent_directories=True)
    except Exception:
        return None


def create_branch_and_commit(
    repo_path: Path,
    branch_name: str,
    commit_message: str,
    files_to_add: List[str]
) -> tuple[bool, str]:
    """
    Create a new branch, add files, and commit changes.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        repo = Repo(repo_path, search_parent_directories=True)
        
        # Check for uncommitted changes
        if repo.is_dirty():
            return False, "Repository has uncommitted changes. Please commit or stash them first."
        
        # Create and checkout new branch
        try:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
        except Exception as e:
            return False, f"Failed to create branch: {e}"
        
        # Add specified files
        for file_path in files_to_add:
            repo.index.add([file_path])
        
        # Commit changes
        repo.index.commit(commit_message)
        
        return True, f"Created branch '{branch_name}' and committed changes"
        
    except Exception as e:
        return False, f"Git operation failed: {e}"


def push_branch(repo_path: Path, branch_name: str, remote: str = "origin") -> tuple[bool, str]:
    """
    Push branch to remote.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        repo = Repo(repo_path, search_parent_directories=True)
        
        # Get remote
        if remote not in [r.name for r in repo.remotes]:
            return False, f"Remote '{remote}' not found"
        
        origin = repo.remote(remote)
        
        # Push branch
        origin.push(branch_name)
        
        return True, f"Pushed branch '{branch_name}' to {remote}"
        
    except Exception as e:
        return False, f"Push failed: {e}"


def create_github_pr(
    repo_owner: str,
    repo_name: str,
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
    token: Optional[str] = None
) -> tuple[bool, str, Optional[str]]:
    """
    Create a GitHub Pull Request.
    
    Args:
        repo_owner: GitHub username or org
        repo_name: Repository name
        branch_name: Source branch for PR
        title: PR title
        body: PR description
        base_branch: Target branch (default: main)
        token: GitHub token (defaults to GITHUB_TOKEN env var)
        
    Returns:
        Tuple of (success, message, pr_url)
    """
    try:
        # Get token from env if not provided
        if token is None:
            token = os.environ.get('GITHUB_TOKEN')
        
        if not token:
            return False, "GitHub token not found. Set GITHUB_TOKEN environment variable.", None
        
        # Initialize GitHub client
        g = Github(token)
        
        # Get repository
        try:
            repo = g.get_repo(f"{repo_owner}/{repo_name}")
        except GithubException as e:
            return False, f"Repository not found: {e}", None
        
        # Create pull request
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=base_branch
            )
            return True, f"Pull request created successfully", pr.html_url
            
        except GithubException as e:
            return False, f"Failed to create PR: {e}", None
        
    except Exception as e:
        return False, f"GitHub operation failed: {e}", None


def get_github_repo_info(repo_path: Path) -> Optional[tuple[str, str]]:
    """
    Extract GitHub owner and repo name from git remote.
    
    Returns:
        Tuple of (owner, repo_name) or None
    """
    try:
        repo = Repo(repo_path, search_parent_directories=True)
        
        # Try to get origin remote URL
        if 'origin' not in [r.name for r in repo.remotes]:
            return None
        
        origin = repo.remote('origin')
        url = origin.url
        
        # Parse GitHub URL (handles both HTTPS and SSH)
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        
        if 'github.com' not in url:
            return None
        
        if url.startswith('git@'):
            # SSH format
            parts = url.split(':')[-1].replace('.git', '').split('/')
        else:
            # HTTPS format
            parts = url.split('github.com/')[-1].replace('.git', '').split('/')
        
        if len(parts) >= 2:
            return parts[0], parts[1]
        
        return None
        
    except Exception:
        return None
