"""
controller.py

Lifecycle control state and operations for deployed apps.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

from aether.subsystems.app_deployer.models import DeploymentRecord, ProcessStatus
from aether.kafka import topics

logger = logging.getLogger("aether.lifecycle_manager.controller")


@dataclass
class LifecycleActionResult:
    app_id: str
    action: str
    status: str
    message: str

    def to_dict(self) -> dict:
        return {
            "app_id": self.app_id,
            "action": self.action,
            "status": self.status,
            "message": self.message,
        }


class LifecycleController:
    def __init__(self):
        self.deployments: Dict[str, DeploymentRecord] = {}
        self.notification_url = os.getenv("AETHER_NOTIFICATION_SERVICE_URL", "http://localhost:8019").rstrip("/")
        self.alert_email = os.getenv("AETHER_ALERT_EMAIL", "")
        self.kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self._kafka_producer = None
        self._init_kafka_producer()

    def register_deployment(self, deployment: DeploymentRecord) -> None:
        self.deployments[deployment.app_id] = deployment

    def register_deployment_dict(self, payload: dict) -> None:
        deployment = DeploymentRecord(
            app_id=payload.get("app_id", ""),
            app_version=payload.get("app_version", ""),
        )
        for process in payload.get("process_records", []):
            deployment.process_records.append(
                self._process_from_dict(process, deployment.app_id, deployment.app_version)
            )
        self.register_deployment(deployment)

    def _process_from_dict(self, process: dict, app_id: str, app_version: str):
        from aether.subsystems.app_deployer.models import ProcessRecord

        return ProcessRecord(
            app_id=app_id,
            app_version=app_version,
            artifact_id=process.get("artifact_id", ""),
            artifact_type=process.get("artifact_type", ""),
            vm_ip=process.get("vm_ip", ""),
            port=process.get("port", 0),
            systemd_service=process.get("systemd_service", ""),
            status=ProcessStatus(process.get("status", ProcessStatus.RUNNING.value)),
        )

    def status(self, app_id: str) -> dict:
        deployment = self.deployments.get(app_id)
        if not deployment:
            return {
                "app_id": app_id,
                "registered": False,
                "message": "No deployment registered",
            }
        return {
            "app_id": deployment.app_id,
            "app_version": deployment.app_version,
            "registered": True,
            "process_count": len(deployment.process_records),
            "processes": [p.to_dict() for p in deployment.process_records],
        }

    def start(self, app_id: str, app_version: Optional[str] = None) -> LifecycleActionResult:
        deployment = self._require_deployment(app_id)
        for process in deployment.process_records:
            process.status = ProcessStatus.RUNNING
        return LifecycleActionResult(app_id, "start", "ok", f"Started {len(deployment.process_records)} processes")

    def stop(self, app_id: str, app_version: Optional[str] = None) -> LifecycleActionResult:
        deployment = self._require_deployment(app_id)
        for process in deployment.process_records:
            process.status = ProcessStatus.STOPPED
        return LifecycleActionResult(app_id, "stop", "ok", f"Stopped {len(deployment.process_records)} processes")

    def restart(self, app_id: str, app_version: Optional[str] = None, reason: str = "") -> LifecycleActionResult:
        deployment = self._require_deployment(app_id)
        for process in deployment.process_records:
            process.status = ProcessStatus.RUNNING
        message = f"Restarted {len(deployment.process_records)} processes"
        if reason:
            message = f"{message} (reason: {reason})"
        self._notify_event(
            event_type="app.restarted",
            app_id=deployment.app_id,
            app_version=app_version or deployment.app_version,
            detail=reason or "Automatic restart from lifecycle manager",
        )
        return LifecycleActionResult(app_id, "restart", "ok", message)

    def scale(self, app_id: str, replicas: int) -> LifecycleActionResult:
        self._require_deployment(app_id)
        return LifecycleActionResult(app_id, "scale", "ok", f"Scale request accepted for replicas={replicas}")

    def rollback(self, app_id: str, target_version: str) -> LifecycleActionResult:
        self._require_deployment(app_id)
        return LifecycleActionResult(app_id, "rollback", "ok", f"Rollback request accepted: target={target_version}")

    def _require_deployment(self, app_id: str) -> DeploymentRecord:
        deployment = self.deployments.get(app_id)
        if not deployment:
            raise ValueError(f"App '{app_id}' is not registered in lifecycle manager")
        return deployment

    def _notify_event(self, event_type: str, app_id: str, app_version: str, detail: str) -> None:
        self._publish_event(
            topics.APP_LIFECYCLE,
            {
                "event_type": event_type,
                "app_id": app_id,
                "app_version": app_version,
                "detail": detail,
            },
        )

    def _init_kafka_producer(self) -> None:
        try:
            from kafka import KafkaProducer  # type: ignore

            self._kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                request_timeout_ms=5000,
            )
        except Exception as exc:
            self._kafka_producer = None
            logger.warning("Kafka unavailable in lifecycle manager (%s).", exc)

    def _publish_event(self, topic: str, payload: dict) -> None:
        if not self._kafka_producer:
            return
        try:
            self._kafka_producer.send(topic, payload)
        except Exception as exc:
            logger.warning("Failed to publish lifecycle event: %s", exc)


controller = LifecycleController()
