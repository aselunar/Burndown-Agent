"""
Azure DevOps client for Backlog Pilot.

Provides integration with Azure DevOps work items and backlogs.
"""

from typing import List, Dict, Any, Optional

from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking import WorkItemTrackingClient
from msrest.authentication import BasicAuthentication

from backlog_pilot.config import Config


class AzureDevOpsClient:
    """Client for interacting with Azure DevOps."""
    
    def __init__(self, config: Config):
        """Initialize Azure DevOps client."""
        self.config = config
        config.validate()
        
        # Create connection
        self.organization_url = f"https://dev.azure.com/{config.azure_org}"
        credentials = BasicAuthentication("", config.azure_token)
        self.connection = Connection(base_url=self.organization_url, creds=credentials)
        
        # Get clients
        self.wit_client: WorkItemTrackingClient = self.connection.clients.get_work_item_tracking_client()
    
    def test_connection(self) -> bool:
        """Test the connection to Azure DevOps."""
        try:
            # Try to get a work item query - simple test
            self.wit_client.get_queries(
                project=self.config.azure_project,
                depth=1
            )
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Azure DevOps: {e}")
    
    def get_backlog_items(
        self,
        limit: int = 10,
        work_item_type: str = "User Story"
    ) -> List[Dict[str, Any]]:
        """
        Get backlog items from Azure DevOps.
        
        Args:
            limit: Maximum number of items to retrieve
            work_item_type: Type of work items to fetch
        
        Returns:
            List of work items
        """
        # WIQL query to get backlog items
        wiql_query = f"""
        SELECT [System.Id], [System.Title], [System.State], [Microsoft.VSTS.Common.Priority]
        FROM WorkItems
        WHERE [System.TeamProject] = '{self.config.azure_project}'
            AND [System.WorkItemType] = '{work_item_type}'
            AND [System.State] <> 'Closed'
            AND [System.State] <> 'Removed'
        ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.CreatedDate] DESC
        """
        
        # Execute query
        wiql = {"query": wiql_query}
        query_results = self.wit_client.query_by_wiql(wiql, top=limit).work_items
        
        if not query_results:
            return []
        
        # Get work item IDs
        work_item_ids = [item.id for item in query_results]
        
        # Get full work item details
        work_items = self.wit_client.get_work_items(
            ids=work_item_ids,
            expand="All"
        )
        
        # Convert to simple dict format
        result = []
        for item in work_items:
            result.append({
                "id": item.id,
                "title": item.fields.get("System.Title", ""),
                "state": item.fields.get("System.State", ""),
                "priority": item.fields.get("Microsoft.VSTS.Common.Priority"),
                "type": item.fields.get("System.WorkItemType", ""),
                "description": item.fields.get("System.Description", ""),
                "assigned_to": item.fields.get("System.AssignedTo", {}).get("displayName") 
                    if item.fields.get("System.AssignedTo") else None,
            })
        
        return result
    
    def get_work_item(self, work_item_id: str) -> Dict[str, Any]:
        """
        Get a specific work item by ID.
        
        Args:
            work_item_id: The work item ID
        
        Returns:
            Work item details
        """
        work_item = self.wit_client.get_work_item(
            id=int(work_item_id),
            expand="All"
        )
        
        return {
            "id": work_item.id,
            "title": work_item.fields.get("System.Title", ""),
            "state": work_item.fields.get("System.State", ""),
            "priority": work_item.fields.get("Microsoft.VSTS.Common.Priority"),
            "type": work_item.fields.get("System.WorkItemType", ""),
            "description": work_item.fields.get("System.Description", ""),
            "assigned_to": work_item.fields.get("System.AssignedTo", {}).get("displayName")
                if work_item.fields.get("System.AssignedTo") else None,
            "url": work_item._links.additional_properties.get("html", {}).get("href", ""),
        }
    
    def update_work_item(
        self,
        work_item_id: str,
        state: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a work item.
        
        Args:
            work_item_id: The work item ID
            state: New state for the work item
            comment: Comment to add
        
        Returns:
            Updated work item
        """
        from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation
        
        document = []
        
        if state:
            document.append(
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.State",
                    value=state
                )
            )
        
        if comment:
            document.append(
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.History",
                    value=comment
                )
            )
        
        work_item = self.wit_client.update_work_item(
            document=document,
            id=int(work_item_id),
            project=self.config.azure_project
        )
        
        return {
            "id": work_item.id,
            "title": work_item.fields.get("System.Title", ""),
            "state": work_item.fields.get("System.State", ""),
        }
