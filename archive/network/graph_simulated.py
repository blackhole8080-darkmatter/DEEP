import random
from typing import Dict, Any

class NetworkGraph:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self._generate_simulated_mesh()

    def _generate_simulated_mesh(self):
        # Center Gateway
        self.nodes.append({
            "id": "gw-01", "layer": "lan", "node_type": "gateway", "label": "DEEP Core Router",
            "metadata": {"ip": "10.0.0.1", "mac": "00:11:22:33:44:55", "vendor": "Cisco", "trust": "trusted"}, 
            "x": 0, "y": 0, "last_seen": "live"
        })
        
        # AI Core Nodes (Dense Cluster)
        for i in range(5):
            self.nodes.append({
                "id": f"ai-core-{i}", "layer": "ai", "node_type": "compute", "label": f"Neural Process 0x{i}",
                "metadata": {"load": random.randint(10, 90), "status": "active", "trust": "trusted"}, 
                "x": 0, "y": 0, "last_seen": "live"
            })
            self.edges.append({
                "source": f"ai-core-{i}", "target": "gw-01", "layer": "lan", "relation": "uplink", "strength": 1.0, "metadata": {}
            })
            for j in range(i):
                self.edges.append({
                    "source": f"ai-core-{i}", "target": f"ai-core-{j}", "layer": "ai", "relation": "synapse", "strength": 0.8, "metadata": {}
                })
        
        # LAN / Wifi / VPN Devices
        for i in range(45):
            r = random.random()
            if r > 0.8: layer = "vpn"
            elif r > 0.4: layer = "wifi"
            else: layer = "lan"
            
            device_type = random.choice(["phone", "laptop", "iot", "sensor", "terminal", "server"])
            node_id = f"dev-{i}"
            self.nodes.append({
                "id": node_id, "layer": layer, "node_type": device_type, "label": f"{device_type.upper()}-{random.randint(100,999)}",
                "metadata": {"ip": f"192.168.{random.randint(1,5)}.{100+i}", "trust": random.choice(["trusted", "unknown"])}, 
                "x": 0, "y": 0, "last_seen": "live"
            })
            self.edges.append({
                "source": node_id, "target": "gw-01", "layer": layer, "relation": "connected", "strength": 0.5, "metadata": {}
            })
            
            # Sub-connections (mesh)
            if random.random() > 0.85:
                peer = f"dev-{random.randint(0, i)}"
                self.edges.append({
                    "source": node_id, "target": peer, "layer": "cross", "relation": "peer", "strength": 0.2, "metadata": {}
                })

        # Internet Threat Nodes
        for i in range(20):
            node_id = f"ext-{i}"
            self.nodes.append({
                "id": node_id, "layer": "internet", "node_type": "external", "label": f"Threat IP {random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "metadata": {"risk": "high", "trust": "blocked"}, "x": 0, "y": 0, "last_seen": "live"
            })
            # Connect to random AI or Gateway
            target = "gw-01" if random.random() > 0.5 else f"ai-core-{random.randint(0,4)}"
            self.edges.append({
                "source": node_id, "target": target, "layer": "internet", "relation": "attack", "strength": 0.9, "metadata": {}
            })

    def export_graph(self, layer=None) -> Dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges
        }
        
    def export_subgraph(self, centre_id: str, depth: int) -> Dict[str, Any]:
        return self.export_graph()

    def stats(self) -> Dict[str, Any]:
        layers = {}
        for n in self.nodes:
            layers[n["layer"]] = layers.get(n["layer"], 0) + 1
        return {"nodes_by_layer": layers}

    def get_observations(self, node_id, metric=None, hours=24):
        return []
        
    def get_inferences(self, node_id, inference_type=None, limit=20):
        return []

net_graph = NetworkGraph()
