"""
GitHub client for Backlog Pilot.

Provides integration with GitHub repositories and pull requests.
"""

from typing import Dict, Any, Optional, List

from github import Github, GithubException

from backlog_pilot.config import Config


class GitHubClient:
    """Client for interacting with GitHub."""
    
    def __init__(self, config: Config):
        """Initialize GitHub client."""
        self.config = config
        config.validate()
        
        # Create GitHub connection
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(config.github_repo)
    
    def test_connection(self) -> bool:
        """Test the connection to GitHub."""
        try:
            # Simple test - get repo info
            _ = self.repo.name
            return True
        except GithubException as e:
            raise ConnectionError(f"Failed to connect to GitHub: {e}")
    
    def create_pr(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a pull request.
        
        Args:
            title: PR title
            body: PR description
            head: Branch to merge from
            base: Branch to merge into (default: main)
        
        Returns:
            Pull request details
        """
        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            
            return {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
                "head": pr.head.ref,
                "base": pr.base.ref,
            }
        except GithubException as e:
            raise Exception(f"Failed to create PR: {e}")
    
    def get_pr(self, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request details.
        
        Args:
            pr_number: PR number
        
        Returns:
            Pull request details
        """
        try:
            pr = self.repo.get_pull(pr_number)
            
            return {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "url": pr.html_url,
                "state": pr.state,
                "head": pr.head.ref,
                "base": pr.base.ref,
                "merged": pr.merged,
                "mergeable": pr.mergeable,
            }
        except GithubException as e:
            raise Exception(f"Failed to get PR: {e}")
    
    def list_prs(
        self,
        state: str = "open",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List pull requests.
        
        Args:
            state: PR state (open, closed, all)
            limit: Maximum number of PRs to return
        
        Returns:
            List of pull requests
        """
        try:
            # Use per_page parameter for efficient pagination
            prs_iterator = self.repo.get_pulls(state=state)
            prs = []
            
            for pr in prs_iterator:
                if len(prs) >= limit:
                    break
                prs.append({
                    "number": pr.number,
                    "title": pr.title,
                    "url": pr.html_url,
                    "state": pr.state,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                })
            
            return prs
        except GithubException as e:
            raise Exception(f"Failed to list PRs: {e}")
    
    def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue.
        
        Args:
            title: Issue title
            body: Issue body
            labels: Issue labels
        
        Returns:
            Issue details
        """
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body or "",
                labels=labels or []
            )
            
            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "state": issue.state,
            }
        except GithubException as e:
            raise Exception(f"Failed to create issue: {e}")
    
    def get_branch(self, branch_name: str) -> Optional[Dict[str, Any]]:
        """
        Get branch details.
        
        Args:
            branch_name: Name of the branch
        
        Returns:
            Branch details or None if not found
        """
        try:
            branch = self.repo.get_branch(branch_name)
            
            return {
                "name": branch.name,
                "sha": branch.commit.sha,
                "protected": branch.protected,
            }
        except GithubException:
            return None
    
    def create_branch(
        self,
        branch_name: str,
        source_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the new branch
            source_branch: Branch to create from
        
        Returns:
            Branch details
        """
        try:
            # Get source branch SHA
            source = self.repo.get_branch(source_branch)
            sha = source.commit.sha
            
            # Create new branch
            ref = self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=sha
            )
            
            return {
                "name": branch_name,
                "sha": sha,
                "ref": ref.ref,
            }
        except GithubException as e:
            raise Exception(f"Failed to create branch: {e}")
