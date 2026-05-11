from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Device:
    device_id: str
    role: str
    zone: str
    process_cell: str
    ip_address: str
    protocols: tuple[str, ...]
    baseline_rate: float
    criticality: str


@dataclass
class SimulationConfig:
    sensors: int = 12
    actuators: int = 6
    plcs: int = 3
    hmis: int = 2
    gateways: int = 1
    historians: int = 1
    batch_size: int = 10
    interval_seconds: float = 0.9
    attack_intensity: float = 0.32
    seed: int = 42
    enabled_attacks: tuple[str, ...] = (
        "burst_flood",
        "rogue_write",
        "lateral_scan",
        "data_exfiltration",
    )


@dataclass
class TrafficRecord:
    timestamp: datetime
    source_device: str
    source_role: str
    source_ip: str
    destination_device: str
    destination_role: str
    destination_ip: str
    protocol: str
    service: str
    function_code: str
    packet_size: int
    latency_ms: float
    jitter_ms: float
    ttl: int
    retransmissions: int
    direction: str
    process_cell: str
    traffic_class: str
    session_id: str
    request_rate_rps: float
    payload_entropy: float
    burst_index: float
    protocol_risk: float
    topology_distance: int
    state: str = "normal"
    attack_name: str = ""
    attack_stage: str = ""
    anomaly_score: float = 0.0
    anomaly_label: str = "normal"
    label: str = "normal"

    def to_dict(self) -> dict[str, object]:
        row = asdict(self)
        row["timestamp"] = self.timestamp.isoformat(timespec="milliseconds")
        return row


@dataclass
class SimulationSnapshot:
    total_records: int = 0
    normal_records: int = 0
    suspicious_records: int = 0
    malicious_records: int = 0
    last_protocol: str = "-"
    active_attack: str = "None"
    average_anomaly_score: float = 0.0
    protocol_counts: dict[str, int] = field(default_factory=dict)
    alert_log: list[str] = field(default_factory=list)
