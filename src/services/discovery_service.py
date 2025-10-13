# -*- coding: utf-8 -*-
"""
Agent Discovery Service

Provides functionality for agents to dynamically discover and register with the Brikk platform.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from src.database import db
from src.models.agent import Agent
from src.models.discovery import AgentService, AgentCapability
from src.services.structured_logging import get_logger

logger = get_logger("brikk.discovery")


class DiscoveryService:
    """Service for managing agent discovery and registration"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.service_ttl_minutes = int(
            os.getenv("AGENT_SERVICE_TTL_MINUTES", "60"))

    def register_service(
            self,
            agent_id: int,
            service_name: str,
            service_url: str,
            capabilities: List[str]) -> AgentService:
        """Register a new service offered by an agent"""
        try:
            # Check if service already exists
            service = self.db.query(AgentService).filter_by(
                agent_id=agent_id,
                name=service_name
            ).first()

            if service:
                # Update existing service
                service.url = service_url
                service.expires_at = datetime.now(
                    timezone.utc) + timedelta(minutes=self.service_ttl_minutes)
                service.updated_at = datetime.now(timezone.utc)
            else:
                # Create new service
                service = AgentService(
                    agent_id=agent_id,
                    name=service_name,
                    url=service_url,
                    expires_at=datetime.now(
                        timezone.utc) +
                    timedelta(
                        minutes=self.service_ttl_minutes))
                self.db.add(service)

            # Update capabilities
            self._update_service_capabilities(service, capabilities)

            self.db.commit()
            logger.info(
                f"Registered service '{service_name}' for agent {agent_id}")
            return service

        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Failed to register service for agent {agent_id}: {e}")
            raise

    def _update_service_capabilities(
            self,
            service: AgentService,
            capabilities: List[str]) -> None:
        """Update the capabilities for a given service"""
        # Remove old capabilities
        self.db.query(AgentCapability).filter_by(
            service_id=service.id).delete()

        # Add new capabilities
        for cap_name in capabilities:
            capability = AgentCapability(service_id=service.id, name=cap_name)
            self.db.add(capability)

    def discover_services(self,
                          capability: Optional[str] = None,
                          organization_id: Optional[int] = None) -> List[Dict[str,
                                                                              Any]]:
        """Discover available agent services, optionally filtered by capability or organization"""
        try:
            query = self.db.query(AgentService).join(Agent).filter(
                AgentService.expires_at > datetime.now(timezone.utc),
                Agent.status == "active"
            )

            if organization_id:
                query = query.filter(Agent.organization_id == organization_id)

            if capability:
                query = query.join(AgentCapability).filter(
                    AgentCapability.name == capability)

            services = query.all()

            return [self._format_service_response(s) for s in services]

        except Exception as e:
            logger.error(f"Failed to discover services: {e}")
            return []

    def get_service_details(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific service"""
        service = self.db.query(AgentService).filter_by(id=service_id).first()
        if not service or service.expires_at <= datetime.now(timezone.utc):
            return None

        return self._format_service_response(service)

    def heartbeat(self, service_id: int) -> bool:
        """Refresh the TTL for a registered service"""
        try:
            service = self.db.query(AgentService).filter_by(
                id=service_id).first()
            if not service:
                return False

            service.expires_at = datetime.now(
                timezone.utc) + timedelta(minutes=self.service_ttl_minutes)
            self.db.commit()
            logger.info(f"Received heartbeat for service {service_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Failed to process heartbeat for service {service_id}: {e}")
            return False

    def remove_expired_services(self) -> int:
        """Remove services that have expired (TTL has passed)"""
        try:
            expired_count = self.db.query(AgentService).filter(
                AgentService.expires_at <= datetime.now(timezone.utc)
            ).delete()

            self.db.commit()
            if expired_count > 0:
                logger.info(f"Removed {expired_count} expired agent services")
            return expired_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove expired services: {e}")
            return 0

    def _format_service_response(
            self, service: AgentService) -> Dict[str, Any]:
        """Format an AgentService object for API responses"""
        return {
            "id": service.id,
            "agent_id": service.agent_id,
            "name": service.name,
            "url": service.url,
            "capabilities": [cap.name for cap in service.capabilities],
            "expires_at": service.expires_at.isoformat(),
            "agent": {
                "id": service.agent.id,
                "name": service.agent.name,
                "organization_id": service.agent.organization_id
            }
        }
