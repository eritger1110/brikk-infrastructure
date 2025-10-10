'''
Workflow Service

Handles the business logic for managing multi-step coordination workflows.
'''

from sqlalchemy.orm import Session

from src.models.workflow import Workflow
from src.models.workflow_step import WorkflowStep
from src.models.workflow_execution import WorkflowExecution

class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(self, name: str, description: str, organization_id: int) -> Workflow:
        workflow = Workflow(name=name, description=description, organization_id=organization_id)
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_workflow(self, workflow_id: int) -> Workflow:
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def get_workflows_by_organization(self, organization_id: int) -> list[Workflow]:
        return self.db.query(Workflow).filter(Workflow.organization_id == organization_id).all()

    def create_workflow_step(self, workflow_id: int, name: str, description: str, agent_id: int, action: str, params: dict, order: int) -> WorkflowStep:
        workflow_step = WorkflowStep(
            workflow_id=workflow_id,
            name=name,
            description=description,
            agent_id=agent_id,
            action=action,
            params=params,
            order=order
        )
        self.db.add(workflow_step)
        self.db.commit()
        self.db.refresh(workflow_step)
        return workflow_step

    def execute_workflow(self, workflow_id: int, context: dict) -> WorkflowExecution:
        workflow_execution = WorkflowExecution(workflow_id=workflow_id, context=context, status="running")
        self.db.add(workflow_execution)
        self.db.commit()
        self.db.refresh(workflow_execution)

        # In a real implementation, this would trigger an asynchronous job
        # to execute the workflow steps. For now, we'll just mark it as running.

        return workflow_execution

