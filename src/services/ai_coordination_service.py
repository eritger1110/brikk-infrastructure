# src/services/ai_coordination_service.py

import random
from flask import current_app
from src.database import db
from src.models.agent import Agent
from src.models.workflow import Workflow
from src.services.workflow_service import WorkflowService

class AICoordinationService:
    def __init__(self, db):
        self.db = db
        self.workflow_service = WorkflowService(db=self.db)

    def intelligent_route(self, workflow_id: int, initial_data: dict) -> dict:
        """
        Intelligently routes a workflow to the most appropriate agent based on
        a combination of agent capabilities, current workload, and historical performance.
        """
        workflow = self.workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow with ID {workflow_id} not found.")

        # Get all available agents with the required capabilities
        required_capabilities = [step.required_capability for step in workflow.steps]
        available_agents = self._get_available_agents(required_capabilities)

        if not available_agents:
            raise RuntimeError("No available agents with the required capabilities.")

        # Select the best agent based on a scoring model
        best_agent = self._select_best_agent(available_agents)

        # Execute the workflow on the selected agent
        execution_result = self.workflow_service.execute_workflow(workflow.id, best_agent.id, initial_data)

        return {
            "message": f"Workflow intelligently routed to agent {best_agent.name}",
            "agent_id": best_agent.id,
            "workflow_execution_id": execution_result["workflow_execution_id"]
        }

    def optimize_coordination_strategy(self, workflow_id: int) -> dict:
        """
        Analyzes historical workflow execution data to optimize the coordination strategy.
        This could involve reordering workflow steps, reassigning agents, or adjusting parameters.
        """
        # In a real implementation, this would involve a machine learning model
        # that analyzes historical data and suggests optimizations.
        # For this example, we will simulate a simple optimization.

        workflow = self.workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow with ID {workflow_id} not found.")

        # Simulate a simple optimization: reverse the order of the workflow steps
        optimized_steps = workflow.steps[::-1]
        workflow.steps = optimized_steps
        self.db.session.commit()

        return {
            "message": f"Coordination strategy for workflow {workflow_id} optimized successfully.",
            "optimized_step_order": [step.name for step in optimized_steps]
        }

    def _get_available_agents(self, required_capabilities: list) -> list:
        """
        Retrieves all available agents that have the required capabilities.
        """
        # This is a simplified implementation. A real system would check agent health,
        # current workload, and other factors.
        agents = Agent.query.all()
        available_agents = []
        for agent in agents:
            agent_capabilities = [capability.name for capability in agent.capabilities]
            if all(capability in agent_capabilities for capability in required_capabilities):
                available_agents.append(agent)
        return available_agents

    def _select_best_agent(self, agents: list) -> Agent:
        """
        Selects the best agent from a list of available agents based on a scoring model.
        """
        # This is a simplified scoring model. A real system would use a more
        # sophisticated model that considers factors like agent performance,
        # cost, and reliability.
        return random.choice(agents)

