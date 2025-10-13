"""
API Connectors

Provides standardized connectors for integrating with external APIs and services.
"""

import os
import json
from typing import Dict, Any, Optional, List

import requests
from requests.auth import AuthBase

from src.services.structured_logging import get_logger

logger = get_logger("brikk.connectors")

class ApiConnector:
    """Base class for API connectors"""
    
    def __init__(self, base_url: str, auth: Optional[AuthBase] = None, default_headers: Optional[Dict] = None):
        self.base_url = base_url
        self.session = requests.Session()
        if auth:
            self.session.auth = auth
        if default_headers:
            self.session.headers.update(default_headers)
            
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Perform a GET request"""
        return self._request("GET", endpoint, params=params, **kwargs)
        
    def post(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Perform a POST request"""
        return self._request("POST", endpoint, data=data, json=json_data, **kwargs)
        
    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """Perform a PUT request"""
        return self._request("PUT", endpoint, data=data, **kwargs)
        
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Perform a DELETE request"""
        return self._request("DELETE", endpoint, **kwargs)
        
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Internal request handling method"""
        url = self.base_url.rstrip("/") + "/" + endpoint.lstrip("/")
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            logger.debug(f"{method} request to {url} successful")
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"API request to {url} failed: {e}")
            raise

class BearerTokenAuth(AuthBase):
    """Bearer token authentication for requests"""
    def __init__(self, token: str):
        self.token = token
        
    def __call__(self, r):
        r.headers["Authorization"] = f"Bearer {self.token}"
        return r

# --- Example Connectors ---

class SlackConnector(ApiConnector):
    """Connector for the Slack API"""
    
    def __init__(self, token: str):
        super().__init__("https://slack.com/api", auth=BearerTokenAuth(token))
        
    def post_message(self, channel: str, text: str, attachments: Optional[List] = None) -> Dict[str, Any]:
        """Post a message to a Slack channel"""
        payload = {
            "channel": channel,
            "text": text,
            "attachments": attachments or []
        }
        response = self.post("chat.postMessage", json_data=payload)
        return response.json()

class JiraConnector(ApiConnector):
    """Connector for the Jira API"""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        super().__init__(base_url)
        self.session.auth = (username, api_token)
        
    def create_issue(self, project_key: str, summary: str, description: str, issue_type: str = "Task") -> Dict[str, Any]:
        """Create a new issue in Jira"""
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type}
            }
        }
        response = self.post("rest/api/2/issue", json_data=payload)
        return response.json()
        
    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get details of a Jira issue"""
        response = self.get(f"rest/api/2/issue/{issue_key}")
        return response.json()

class GitHubConnector(ApiConnector):
    """Connector for the GitHub API"""
    
    def __init__(self, token: str):
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}"
        }
        super().__init__("https://api.github.com", default_headers=headers)
        
    def create_repo(self, name: str, description: str = "", private: bool = False) -> Dict[str, Any]:
        """Create a new GitHub repository"""
        payload = {
            "name": name,
            "description": description,
            "private": private
        }
        response = self.post("user/repos", json_data=payload)
        return response.json()
        
    def get_user_repos(self, username: str) -> List[Dict[str, Any]]:
        """Get repositories for a user"""
        response = self.get(f"users/{username}/repos")
        return response.json()

# --- Factory for creating connectors ---

def get_connector(service_name: str, config: Dict[str, Any]) -> Optional[ApiConnector]:
    """Factory function to get an API connector instance"""
    if service_name == "slack":
        token = config.get("token") or os.getenv("SLACK_API_TOKEN")
        if not token:
            raise ValueError("Slack token not provided")
        return SlackConnector(token)
        
    elif service_name == "jira":
        base_url = config.get("base_url") or os.getenv("JIRA_BASE_URL")
        username = config.get("username") or os.getenv("JIRA_USERNAME")
        api_token = config.get("api_token") or os.getenv("JIRA_API_TOKEN")
        if not all([base_url, username, api_token]):
            raise ValueError("Jira configuration incomplete")
        return JiraConnector(base_url, username, api_token)
        
    elif service_name == "github":
        token = config.get("token") or os.getenv("GITHUB_API_TOKEN")
        if not token:
            raise ValueError("GitHub token not provided")
        return GitHubConnector(token)
        
    else:
        logger.warning(f"Unknown connector service: {service_name}")
        return None

