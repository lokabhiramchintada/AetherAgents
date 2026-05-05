"""
distributor.py

Reads distribution.nodes from config.yaml and maps each node to an available VM.

The distributor:
  1. Parses config.yaml distribution topology
  2. Queries VM health checker for available VMs
  3. Selects healthiest VM matching each node's role/requirements
  4. Augments distribution nodes with VM assignments (vm_ip, etc)
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("aether.deployer.distributor")


def parse_distribution_config(config_path: Path) -> Dict[str, Any]:
    """
    Parse config.yaml and extract distribution topology.
    
    Args:
        config_path: Path to config.yaml
    
    Returns:
        {
            "mode": "distributed",
            "nodes": [
                {
                    "node_id": "agent-node-1",
                    "role": "agent",
                    "host": "localhost",
                    "port": 8001,
                    "artifacts": ["email-classifier-agent"],
                }
            ]
        }
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    distribution = config.get("distribution", {})
    
    return {
        "mode": distribution.get("mode", "local"),
        "topology": distribution.get("topology", "monolithic"),
        "transport": distribution.get("transport", "http"),
        "nodes": distribution.get("nodes", []),
    }


class VMPool:
    """
    Represents the pool of available VMs from vm_pool.json.
    
    This is a simplified version — in production, this would query
    the VM Health Checker subsystem via Kafka or HTTP.
    """
    
    def __init__(self):
        """Initialize VM pool."""
        self.vms: List[Dict[str, Any]] = []
    
    def load_from_file(self, vm_pool_path: Path) -> None:
        """Load VM pool from JSON file."""
        with open(vm_pool_path, "r") as f:
            import json
            data = json.load(f)
            self.vms = data.get("vms", [])
        
        logger.info(f"Loaded {len(self.vms)} VMs from pool")
    
    def find_healthy_vm(self, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a healthy VM matching the given role.
        
        Args:
            role: Node role to match (agent, tool, orchestrator, model, any)
        
        Returns:
            VM record if found, None otherwise
        
        VM record schema:
            {
                "name": "vm-1",
                "ip": "192.168.1.10",
                "roles": ["agent", "tool"],  # capabilities
                "status": "healthy",
                "cpu_pct": 25.0,
                "ram_pct": 60.0,
                "latency_ms": 2.5,
            }
        """
        # Filter healthy VMs with matching role
        candidates = [
            vm for vm in self.vms
            if vm.get("status") == "healthy"
            and (role is None or role in vm.get("roles", []))
        ]
        
        if not candidates:
            return None
        
        # Sort by least-loaded (CPU first, then RAM)
        candidates.sort(
            key=lambda vm: (
                vm.get("cpu_pct", 100),
                vm.get("ram_pct", 100),
            )
        )
        
        return candidates[0]
    
    def find_vms_for_distribution(
        self,
        nodes: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Assign VMs to distribution nodes.
        
        Args:
            nodes: List of distribution nodes from config.yaml
        
        Returns:
            Mapping of node_id → assigned VM record
        
        Raises:
            RuntimeError: If insufficient VMs available
        """
        assignments = {}
        
        for node in nodes:
            node_id = node.get("node_id")
            role = node.get("role")
            
            vm = self.find_healthy_vm(role)
            if not vm:
                raise RuntimeError(
                    f"No healthy VM available for node {node_id} (role: {role})"
                )
            
            assignments[node_id] = vm
            logger.info(f"Assigned {node_id} → {vm['name']} ({vm['ip']})")
        
        return assignments


class Distributor:
    """
    Orchestrates VM assignment and distribution node augmentation.
    """
    
    def __init__(self, vm_pool: Optional[VMPool] = None):
        """
        Initialize distributor.
        
        Args:
            vm_pool: VMPool instance (or None to use default)
        """
        self.vm_pool = vm_pool or VMPool()
    
    def distribute(
        self,
        config_path: Path,
        vm_pool_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Parse distribution config and assign VMs to nodes.
        
        Args:
            config_path: Path to config.yaml
            vm_pool_path: Path to vm_pool.json (optional)
        
        Returns:
            Augmented distribution config with vm_ip assigned to each node:
            {
                "mode": "distributed",
                "nodes": [
                    {
                        "node_id": "agent-node-1",
                        "role": "agent",
                        "port": 8001,
                        "artifacts": [...],
                        "vm_ip": "192.168.1.10",      # ← assigned by distributor
                        "vm_name": "vm-1",             # ← assigned by distributor
                    }
                ]
            }
        """
        logger.info(f"Reading distribution config: {config_path}")
        
        # Load distribution topology
        distribution = parse_distribution_config(config_path)
        nodes = distribution.get("nodes", [])
        
        logger.info(f"Found {len(nodes)} nodes to distribute")
        
        # Load VM pool if path provided
        if vm_pool_path:
            logger.info(f"Loading VM pool: {vm_pool_path}")
            self.vm_pool.load_from_file(vm_pool_path)
        
        # Assign VMs to nodes
        vm_assignments = self.vm_pool.find_vms_for_distribution(nodes)
        
        # Augment nodes with VM assignments
        for node in nodes:
            node_id = node.get("node_id")
            if node_id in vm_assignments:
                vm = vm_assignments[node_id]
                node["vm_ip"] = vm.get("ip")
                node["vm_name"] = vm.get("name")
            else:
                logger.warning(f"No VM assigned to {node_id}")
        
        logger.info(f"✓ Distribution complete: {len(nodes)} nodes assigned to VMs")
        
        return distribution


def main():
    """CLI entry point for testing."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Distribute app nodes across VM pool"
    )
    parser.add_argument("config", type=Path, help="Path to config.yaml")
    parser.add_argument("--vm-pool", type=Path, help="Path to vm_pool.json")
    parser.add_argument("--output", type=Path, help="Output augmented config to file")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    distributor = Distributor()
    result = distributor.distribute(args.config, args.vm_pool)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Wrote augmented config to {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import sys
    sys.exit(main())
