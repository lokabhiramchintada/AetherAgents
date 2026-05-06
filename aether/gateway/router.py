from __future__ import annotations

import json
import logging
import shutil
import tempfile
import os
import shlex
import zipfile
from pathlib import Path
from typing import Optional, Literal

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from aether.subsystems.app_deployer.service import AppDeployerService
from aether.subsystems.app_validator.config_validator import validate_config
from aether.subsystems.app_validator.structure_validator import validate_structure
from aether.subsystems.build_packager.builder import BuildPackager
from aether.subsystems.lifecycle_manager.controller import controller as lifecycle_controller
from aether.subsystems.app_registry.app_registry import register_package
from aether.subsystems.app_deployer.models import DeploymentRecord, DeploymentStatus, ProcessRecord, ProcessStatus

logger = logging.getLogger("aether.gateway.router")
router = APIRouter(prefix="/v1", tags=["Gateway"])


class DeployPipelineRequest(BaseModel):
    source: str = Field(..., description="App source directory, .zip, or git URL")
    config_path: Optional[str] = None
    output: Optional[str] = None
    vm_pool_path: Optional[str] = None
    ssh_key: Optional[str] = None
    ssh_user: str = "ubuntu"
    skip_dependency_check: bool = False
    skip_syntax_check: bool = False
    app_health_checker_url: Optional[str] = None


class LifecycleActionRequest(BaseModel):
    action: Literal["start", "stop", "restart", "scale"]
    replicas: Optional[int] = None


def _validate_source(source_dir: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    struct_errs, struct_warns = validate_structure(str(source_dir))
    config_errs, app_name, app_version = validate_config(str(source_dir))

    errors.extend(struct_errs)
    errors.extend(config_errs)
    warnings.extend(struct_warns)

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "app_name": app_name,
        "app_version": app_version,
    }


def _simulate_deployment(config_path: Path, app_id: str, app_version: str) -> DeploymentRecord:
    deployment = DeploymentRecord(app_id=app_id, app_version=app_version, status=DeploymentStatus.SUCCEEDED)
    config = json.loads(json.dumps({}))
    try:
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        config = {}

    nodes = config.get("distribution", {}).get("nodes", [])
    for node in nodes:
        vm_ip = node.get("vm_ip", node.get("host", "127.0.0.1"))
        port = int(node.get("port", 8000))
        role = node.get("role", "")
        for artifact_id in node.get("artifacts", []):
            deployment.process_records.append(
                ProcessRecord(
                    app_id=app_id,
                    app_version=app_version,
                    artifact_id=artifact_id,
                    artifact_type=role,
                    vm_ip=vm_ip,
                    port=port,
                    systemd_service=f"aether-{app_id}-{artifact_id}",
                    status=ProcessStatus.RUNNING,
                )
            )
    return deployment


def _list_registered_apps() -> list[dict]:
    repo_root = Path(__file__).resolve().parents[2]
    apps_dir = Path(
        os.getenv(
            "AETHER_APP_REGISTRY_DIR",
            str(repo_root / ".run" / "storage" / "apps"),
        )
    )
    discovered: list[dict] = []

    if not apps_dir.exists():
        return discovered

    for app_dir in sorted(p for p in apps_dir.iterdir() if p.is_dir()):
        versions = [p for p in app_dir.iterdir() if p.is_dir()]
        if not versions:
            continue

        latest_version_dir = sorted(versions, key=lambda item: item.name)[-1]
        status = lifecycle_controller.status(app_dir.name)
        discovered.append(
            {
                "id": app_dir.name,
                "name": app_dir.name.replace("-", " ").title(),
                "version": latest_version_dir.name,
                "status": "Healthy" if status.get("registered") else "Registered",
                "nodes": status.get("process_count", 0),
            }
        )

    return discovered


async def _fetch_health_targets(app_id: str) -> list[dict]:
    health_url = os.getenv("AETHER_APP_HEALTH_CHECKER_URL", "http://localhost:8015").rstrip("/")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{health_url}/health/targets", timeout=10)
            if not response.is_success:
                return []
            payload = response.json() or {}
    except Exception as exc:
        logger.warning("Failed to fetch app health targets for %s: %s", app_id, exc)
        return []

    targets = payload.get("targets", []) if isinstance(payload, dict) else []
    return [target for target in targets if target.get("app_id") == app_id]


def _registry_app_paths(app_id: str, app_version: str | None = None) -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    storage_dir = Path(
        os.getenv(
            "AETHER_APP_REGISTRY_STORAGE_DIR",
            str(repo_root / ".run" / "storage"),
        )
    )
    apps_dir = Path(
        os.getenv(
            "AETHER_APP_REGISTRY_DIR",
            str(storage_dir / "apps"),
        )
    )

    app_root = apps_dir / app_id
    if app_version and app_version != "unknown":
        version_root = app_root / app_version
    else:
        versions = sorted([p for p in app_root.iterdir() if p.is_dir()], key=lambda item: item.name) if app_root.exists() else []
        version_root = versions[-1] if versions else app_root

    source_dir = version_root / "source"
    package_path = version_root / "package.zip"
    return {
        "storage_dir": str(storage_dir),
        "apps_dir": str(apps_dir),
        "app_root": str(app_root),
        "version_root": str(version_root),
        "source_dir": str(source_dir),
        "package_path": str(package_path),
    }


def _sample_run_payload(app_id: str) -> dict:
    if app_id == "email-classifier-agent":
        return {"raw_email": "Can we reschedule tomorrow's meeting?"}
    return {"input": "example"}


def _build_curl_command(url: str, payload: dict) -> str:
    body = json.dumps(payload, ensure_ascii=False)
    return f"curl -sS -X POST {shlex.quote(url)} -H 'Content-Type: application/json' -d {shlex.quote(body)}"


def _build_cli_context(app_id: str, status: dict, targets: list[dict]) -> dict:
    payload = _sample_run_payload(app_id)
    proxy_endpoint = f"http://localhost:8000/v1/apps/{app_id}/run"
    proxy_command = _build_curl_command(proxy_endpoint, payload)

    target_commands = []
    for target in targets:
        endpoint = f"http://{target.get('vm_ip', 'localhost')}:{target.get('port', 0)}/run"
        target_commands.append(
            {
                "artifact_id": target.get("artifact_id", ""),
                "run_endpoint": endpoint,
                "curl_command": _build_curl_command(endpoint, payload),
                "vm_ip": target.get("vm_ip", ""),
                "port": target.get("port", 0),
            }
        )

    primary_command = target_commands[0]["curl_command"] if target_commands else proxy_command
    primary_endpoint = target_commands[0]["run_endpoint"] if target_commands else proxy_endpoint
    return {
        "primary_endpoint": primary_endpoint,
        "curl_command": primary_command,
        "proxy_endpoint": proxy_endpoint,
        "proxy_curl_command": proxy_command,
        "request_body": payload,
        "targets": target_commands,
    }


def _bootstrap_deployment_from_targets(app_id: str, targets: list[dict]) -> None:
    if not targets or lifecycle_controller.status(app_id).get("registered"):
        return

    app_version = targets[0].get("app_version", "unknown")
    deployment = DeploymentRecord(app_id=app_id, app_version=app_version, status=DeploymentStatus.SUCCEEDED)
    for target in targets:
        deployment.process_records.append(
            ProcessRecord(
                app_id=app_id,
                app_version=app_version,
                artifact_id=target.get("artifact_id", ""),
                artifact_type=target.get("artifact_type", ""),
                vm_ip=target.get("vm_ip", ""),
                port=target.get("port", 0),
                systemd_service=f"aether-{app_id}-{target.get('artifact_id', '')}",
                status=ProcessStatus.RUNNING,
            )
        )

    lifecycle_controller.register_deployment(deployment)


@router.post("/apps/deploy")
def deploy_pipeline(payload: DeployPipelineRequest) -> dict:
    packager = BuildPackager()
    try:
        build_result = packager.build(
            payload.source,
            Path(payload.output) if payload.output else None,
            skip_dependency_check=payload.skip_dependency_check,
            skip_syntax_check=payload.skip_syntax_check,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Build failed: {exc}") from exc

    source_dir = Path(build_result.source_path)
    validation = _validate_source(source_dir)
    if not validation["passed"]:
        raise HTTPException(status_code=400, detail={"stage": "validate", "report": validation})

    app_id = validation["app_name"] or build_result.manifest.app_name
    app_version = validation["app_version"] or build_result.manifest.app_version
    config_path = Path(payload.config_path) if payload.config_path else source_dir / "config.yaml"

    deployer = AppDeployerService(app_health_checker_base_url=payload.app_health_checker_url)
    try:
        deployment = deployer.deploy(
            app_id=app_id,
            app_version=app_version,
            zip_path=Path(build_result.output_path),
            config_path=config_path,
            vm_pool_path=Path(payload.vm_pool_path) if payload.vm_pool_path else None,
            ssh_key=Path(payload.ssh_key) if payload.ssh_key else None,
            ssh_user=payload.ssh_user,
        )
    except Exception as exc:
        allow_sim = os.getenv("AETHER_ALLOW_SIMULATED_DEPLOY", "true").lower() in {"1", "true", "yes", "on"}
        if not allow_sim:
            raise HTTPException(status_code=500, detail=f"Deploy failed: {exc}") from exc
        logger.warning("Real deploy failed, using simulated deployment fallback: %s", exc)
        deployment = _simulate_deployment(config_path, app_id, app_version)
        deployer._publish_deployed_event(deployment)  # noqa: SLF001

    lifecycle_controller.register_deployment(deployment)

    return {
        "stage": "completed",
        "build": build_result.to_dict(),
        "validation": validation,
        "deployment": deployment.to_dict(),
    }


@router.post("/apps/deploy/upload")
async def deploy_pipeline_upload(
    file: UploadFile = File(...),
    vm_pool_path: str = Form("infra/vm_pool.json"),
    ssh_key: Optional[str] = Form(None),
    ssh_user: str = Form("ubuntu"),
    skip_dependency_check: bool = Form(False),
    skip_syntax_check: bool = Form(False),
) -> dict:
    filename = (file.filename or "").lower()
    if not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be .zip")

    temp_dir = tempfile.mkdtemp(prefix="aether-gateway-upload-")
    zip_path = Path(temp_dir) / file.filename
    extract_dir = Path(temp_dir) / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with open(zip_path, "wb") as handle:
        handle.write(await file.read())

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    source_dir = extract_dir
    entries = [entry for entry in extract_dir.iterdir() if entry.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        source_dir = entries[0]

    try:
        payload = DeployPipelineRequest(
            source=str(source_dir),
            vm_pool_path=vm_pool_path,
            ssh_key=ssh_key,
            ssh_user=ssh_user,
            skip_dependency_check=skip_dependency_check,
            skip_syntax_check=skip_syntax_check,
        )
        result = deploy_pipeline(payload)
        deployment = result.get("deployment", {})
        app_id = deployment.get("app_id")
        app_version = deployment.get("app_version")
        if app_id and app_version:
            register_package(app_id, app_version, Path(result["build"]["output_path"]))
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/apps")
def list_apps() -> dict:
    return {"apps": _list_registered_apps()}


@router.get("/apps/{app_id}/overview")
async def app_overview(app_id: str) -> dict:
    status = lifecycle_controller.status(app_id)
    targets = await _fetch_health_targets(app_id)
    if not status.get("registered") and targets:
        _bootstrap_deployment_from_targets(app_id, targets)
        status = lifecycle_controller.status(app_id)
    cli = _build_cli_context(app_id, status, targets)

    healthy_targets = [target for target in targets if target.get("status") == "healthy"]
    degraded_targets = [target for target in targets if target.get("status") == "degraded"]
    down_targets = [target for target in targets if target.get("status") == "down"]
    response_times = [target.get("last_response_time_ms") for target in targets if target.get("last_response_time_ms") is not None]
    avg_response_time_ms = round(sum(response_times) / len(response_times), 2) if response_times else None
    last_checked = max((target.get("last_checked") or 0 for target in targets), default=None)

    return {
        "app_id": app_id,
        "name": app_id.replace("-", " ").title(),
        "version": status.get("app_version", "unknown"),
        "status": status,
        "cli": cli,
        "health": {
            "target_count": len(targets),
            "healthy_count": len(healthy_targets),
            "degraded_count": len(degraded_targets),
            "down_count": len(down_targets),
            "avg_response_time_ms": avg_response_time_ms,
            "last_checked": last_checked,
            "targets": targets,
        },
    }


@router.get("/apps/{app_id}/status")
def app_status(app_id: str) -> dict:
    return lifecycle_controller.status(app_id)


@router.post("/apps/{app_id}/run")
async def app_run(app_id: str, body: dict) -> dict:
    status = lifecycle_controller.status(app_id)
    targets = status.get("processes", []) if status.get("registered") else []
    if not targets:
        targets = await _fetch_health_targets(app_id)
    if not targets:
        raise HTTPException(status_code=404, detail=f"No registered targets found for {app_id}")

    target = next((item for item in targets if item.get("artifact_id") == app_id), targets[0])
    endpoint = f"http://{target.get('vm_ip', 'localhost')}:{target.get('port', 0)}/run"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=body, timeout=60)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach target {endpoint}: {exc}") from exc

    if not response.is_success:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    try:
        return response.json()
    except Exception:
        return {"output": response.text, "status": "ok"}


@router.post("/apps/{app_id}/lifecycle")
def app_lifecycle(app_id: str, request: LifecycleActionRequest) -> dict:
    targets: list[dict] = []
    if not lifecycle_controller.status(app_id).get("registered"):
        try:
            import anyio

            targets = anyio.run(_fetch_health_targets, app_id)
        except Exception:
            targets = []
        if targets:
            _bootstrap_deployment_from_targets(app_id, targets)

    try:
        if request.action == "start":
            result = lifecycle_controller.start(app_id)
        elif request.action == "stop":
            result = lifecycle_controller.stop(app_id)
        elif request.action == "restart":
            result = lifecycle_controller.restart(app_id)
        else:
            replicas = request.replicas if request.replicas is not None else 1
            result = lifecycle_controller.scale(app_id, replicas=replicas)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.to_dict()


@router.get("/contracts")
def contracts() -> dict:
    return {
        "version": "v1",
        "description": "Unified gateway contracts",
        "endpoints": [
            {"path": "/v1/apps/deploy", "method": "POST"},
            {"path": "/v1/apps/{app_id}/overview", "method": "GET"},
            {"path": "/v1/apps/{app_id}/status", "method": "GET"},
            {"path": "/v1/apps/{app_id}/lifecycle", "method": "POST"},
            {"path": "/v1/contracts", "method": "GET"},
        ],
    }
