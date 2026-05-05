"""
service.py

Main service interface for app deployment.

Orchestrates:
  1. Distributor — map nodes to VMs
  2. RuntimeGenerator — create _aether_main.py
  3. AppDeployer — SSH/SCP/pip to each VM
  4. ProcessManager — systemd unit generation and launching

This is the public API that the platform (gateway, orchestrators)
calls when deploying an app.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from .distributor import Distributor, parse_distribution_config
from .deployer import AppDeployer, SSHConnection
from .process_manager import ProcessManager, ServiceConfig
from .runtime_generator import RuntimeGenerator
from .models import DeploymentRecord, DeploymentStatus, ProcessRecord, ProcessStatus

logger = logging.getLogger("aether.deployer.service")


class AppDeployerService:
    """
    Main service for deploying Aether applications.
    
    Public methods:
      - deploy(app_id, app_version, zip_path, config_path, vm_pool_path)
      - rollback(deployment_record)
      - start(deployment_record)
      - stop(deployment_record)
      - status(deployment_record)
    """
    
    def __init__(
        self,
        runtime_generator: Optional[RuntimeGenerator] = None,
        distributor: Optional[Distributor] = None,
    ):
        """Initialize service with optional dependency injection."""
        self.runtime_generator = runtime_generator or RuntimeGenerator()
        self.distributor = distributor or Distributor()
    
    def deploy(
        self,
        app_id: str,
        app_version: str,
        zip_path: Path,
        config_path: Path,
        vm_pool_path: Optional[Path] = None,
        ssh_key: Optional[Path] = None,
        ssh_user: str = "ubuntu",
    ) -> DeploymentRecord:
        """
        Deploy an application across the VM pool.
        
        Workflow:
          1. Distribute nodes across VMs (via Distributor)
          2. For each VM:
             a. Connect via SSH
             b. Deploy app ZIP
             c. Generate _aether_main.py
          3. For each artifact:
             a. Generate systemd unit
             b. Start process
             c. Wait for /health ready
        
        Args:
            app_id: Application ID
            app_version: Version
            zip_path: Local path to app.zip
            config_path: Local path to config.yaml
            vm_pool_path: Path to vm_pool.json
            ssh_key: Path to SSH private key
            ssh_user: SSH username
        
        Returns:
            DeploymentRecord with status and process records
        
        Raises:
            RuntimeError: If deployment fails
        """
        logger.info(f"=" * 70)
        logger.info(f"Starting deployment: {app_id} v{app_version}")
        logger.info(f"=" * 70)
        
        deployment = DeploymentRecord(
            app_id=app_id,
            app_version=app_version,
            status=DeploymentStatus.IN_PROGRESS,
        )
        
        try:
            # Step 1: Distribute nodes across VMs
            logger.info("Step 1: Distributing nodes across VMs...")
            distribution = self.distributor.distribute(config_path, vm_pool_path)
            nodes = distribution.get("nodes", [])
            
            if not nodes:
                raise RuntimeError("No distribution nodes found in config.yaml")
            
            # Step 2: Group nodes by VM
            nodes_by_vm = self._group_nodes_by_vm(nodes)
            logger.info(f"Deploying to {len(nodes_by_vm)} VMs")
            
            # Step 3: Deploy to each VM
            for vm_ip, vm_nodes in nodes_by_vm.items():
                logger.info(f"\nDeploying to VM: {vm_ip}")
                self._deploy_to_vm(
                    vm_ip=vm_ip,
                    app_id=app_id,
                    app_version=app_version,
                    zip_path=zip_path,
                    config_path=config_path,
                    nodes=vm_nodes,
                    deployment=deployment,
                    ssh_key=ssh_key,
                    ssh_user=ssh_user,
                )
            
            # All steps succeeded
            deployment.status = DeploymentStatus.SUCCEEDED
            logger.info(f"✓ Deployment succeeded")
            
        except Exception as e:
            logger.error(f"✗ Deployment failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            raise
        
        return deployment
    
    def _group_nodes_by_vm(self, nodes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group distribution nodes by VM IP."""
        grouped = {}
        for node in nodes:
            vm_ip = node.get("vm_ip", "localhost")
            if vm_ip not in grouped:
                grouped[vm_ip] = []
            grouped[vm_ip].append(node)
        return grouped
    
    def _deploy_to_vm(
        self,
        vm_ip: str,
        app_id: str,
        app_version: str,
        zip_path: Path,
        config_path: Path,
        nodes: List[Dict[str, Any]],
        deployment: DeploymentRecord,
        ssh_key: Optional[Path] = None,
        ssh_user: str = "ubuntu",
    ) -> None:
        """Deploy to a single VM."""
        logger.info(f"Connecting to {vm_ip} as {ssh_user}...")
        
        # Connect via SSH
        ssh = SSHConnection(
            hostname=vm_ip,
            username=ssh_user,
            key_filename=str(ssh_key) if ssh_key else None,
        )
        ssh.connect()
        
        try:
            # Deploy app to VM (SSH/SCP/pip)
            app_deployer = AppDeployer(ssh)
            app_deployer.deploy(app_id, app_version, zip_path, config_path)
            
            # Generate and start processes
            process_manager = ProcessManager(ssh)
            
            for node in nodes:
                logger.info(f"Starting processes for node: {node.get('node_id')}")
                
                artifacts = node.get("artifacts", [])
                role = node.get("role", "")
                port = node.get("port", 8000)
                
                for artifact_id in artifacts:
                    config = ServiceConfig(
                        app_id=app_id,
                        app_version=app_version,
                        artifact_id=artifact_id,
                        artifact_type=role,
                        port=port,
                        vm_ip=vm_ip,
                    )
                    
                    # Start process
                    process_manager.start_process(config, wait_for_ready=True)
                    
                    # Record process
                    process_rec = ProcessRecord(
                        app_id=app_id,
                        app_version=app_version,
                        artifact_id=artifact_id,
                        artifact_type=role,
                        vm_ip=vm_ip,
                        port=port,
                        systemd_service=config.service_name,
                        status=ProcessStatus.RUNNING,
                    )
                    deployment.process_records.append(process_rec)
        
        finally:
            ssh.close()
    
    def status(self, deployment: DeploymentRecord) -> Dict[str, Any]:
        """
        Get status of a deployment.
        
        Args:
            deployment: DeploymentRecord
        
        Returns:
            Status dict with process states
        """
        return {
            "deployment_id": deployment.deployment_id,
            "app_id": deployment.app_id,
            "status": deployment.status.value,
            "process_count": len(deployment.process_records),
            "processes": [p.to_dict() for p in deployment.process_records],
        }


def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy an Aether application"
    )
    parser.add_argument("--app-id", required=True, help="App ID")
    parser.add_argument("--app-version", required=True, help="Version")
    parser.add_argument("--zip", type=Path, required=True, help="Path to app.zip")
    parser.add_argument("--config", type=Path, required=True, help="Path to config.yaml")
    parser.add_argument("--vm-pool", type=Path, help="Path to vm_pool.json")
    parser.add_argument("--key", type=Path, help="SSH private key")
    parser.add_argument("--user", default="ubuntu", help="SSH user")
    parser.add_argument("--output", type=Path, help="Save deployment record to JSON")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    service = AppDeployerService()
    deployment = service.deploy(
        app_id=args.app_id,
        app_version=args.app_version,
        zip_path=args.zip,
        config_path=args.config,
        vm_pool_path=args.vm_pool,
        ssh_key=args.key,
        ssh_user=args.user,
    )
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(deployment.to_dict(), f, indent=2)
        logger.info(f"Saved deployment record to {args.output}")
    else:
        print(json.dumps(deployment.to_dict(), indent=2))


if __name__ == "__main__":
    import sys
    sys.exit(main())
