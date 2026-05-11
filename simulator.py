from __future__ import annotations

import csv
import random
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

from models import Device, SimulationConfig, SimulationSnapshot, TrafficRecord


ROLE_PROTOCOLS: dict[str, tuple[str, ...]] = {
    "sensor": ("MQTT", "Modbus TCP"),
    "actuator": ("Modbus TCP", "OPC UA"),
    "plc": ("Modbus TCP", "OPC UA", "DNP3"),
    "hmi": ("OPC UA", "HTTP", "MQTT"),
    "gateway": ("MQTT", "HTTPS", "OPC UA"),
    "historian": ("HTTPS", "MQTT", "OPC UA"),
    "external": ("HTTPS",),
}

PROTOCOL_SERVICES: dict[str, tuple[tuple[str, str], ...]] = {
    "MQTT": (
        ("telemetry/publish", "PUBLISH"),
        ("command/subscribe", "SUBSCRIBE"),
        ("state/heartbeat", "KEEPALIVE"),
    ),
    "Modbus TCP": (
        ("holding-registers", "03 Read Holding Registers"),
        ("coils", "01 Read Coils"),
        ("write-registers", "16 Write Multiple Registers"),
    ),
    "OPC UA": (
        ("session/create", "CreateSession"),
        ("telemetry/read", "Read"),
        ("control/write", "Write"),
    ),
    "DNP3": (
        ("polling/read", "Read Binary Input"),
        ("outstation/write", "Operate"),
    ),
    "HTTP": (
        ("dashboard/get", "GET"),
        ("setpoint/post", "POST"),
    ),
    "HTTPS": (
        ("historian/upload", "POST"),
        ("cloud/sync", "PUT"),
        ("backup/export", "POST"),
    ),
}

ROLE_TRAFFIC_CLASS: dict[str, tuple[str, ...]] = {
    "sensor": ("telemetry", "cyclical"),
    "actuator": ("control", "response"),
    "plc": ("control", "orchestration"),
    "hmi": ("supervisory", "operator"),
    "gateway": ("aggregation", "bridge"),
    "historian": ("historian", "replication"),
}

ROLE_PACKET_SIZE: dict[str, tuple[int, int]] = {
    "sensor": (120, 380),
    "actuator": (150, 420),
    "plc": (220, 680),
    "hmi": (260, 900),
    "gateway": (300, 1150),
    "historian": (400, 1400),
}

ATTACK_DISPLAY_NAMES: dict[str, str] = {
    "burst_flood": "Burst Flood",
    "rogue_write": "Rogue PLC Write",
    "lateral_scan": "Lateral Scan",
    "data_exfiltration": "Data Exfiltration",
}


class NetworkTopologyGenerator:
    def __init__(self, config: SimulationConfig, rng: random.Random) -> None:
        self.config = config
        self.rng = rng

    def generate(self) -> list[Device]:
        devices: list[Device] = []
        cell_count = max(2, self.config.plcs)
        cell_names = [f"Cell-{index + 1}" for index in range(cell_count)]
        ip_pool: dict[str, int] = defaultdict(lambda: 10)

        def next_ip(zone: str) -> str:
            third_octet = 20 if zone == "Operations" else 40
            ip_pool[zone] += 1
            return f"10.24.{third_octet}.{ip_pool[zone]}"

        for index in range(self.config.gateways):
            devices.append(
                Device(
                    device_id=f"GW-{index + 1:02d}",
                    role="gateway",
                    zone="DMZ",
                    process_cell="Backbone",
                    ip_address=next_ip("DMZ"),
                    protocols=ROLE_PROTOCOLS["gateway"],
                    baseline_rate=10.0,
                    criticality="high",
                )
            )

        for index in range(self.config.historians):
            devices.append(
                Device(
                    device_id=f"HIST-{index + 1:02d}",
                    role="historian",
                    zone="DMZ",
                    process_cell="Backbone",
                    ip_address=next_ip("DMZ"),
                    protocols=ROLE_PROTOCOLS["historian"],
                    baseline_rate=7.5,
                    criticality="high",
                )
            )

        for index in range(self.config.plcs):
            cell = cell_names[index % len(cell_names)]
            devices.append(
                Device(
                    device_id=f"PLC-{index + 1:02d}",
                    role="plc",
                    zone="Operations",
                    process_cell=cell,
                    ip_address=next_ip("Operations"),
                    protocols=ROLE_PROTOCOLS["plc"],
                    baseline_rate=12.0,
                    criticality="critical",
                )
            )

        for index in range(self.config.hmis):
            cell = cell_names[index % len(cell_names)]
            devices.append(
                Device(
                    device_id=f"HMI-{index + 1:02d}",
                    role="hmi",
                    zone="Operations",
                    process_cell=cell,
                    ip_address=next_ip("Operations"),
                    protocols=ROLE_PROTOCOLS["hmi"],
                    baseline_rate=5.0,
                    criticality="high",
                )
            )

        for index in range(self.config.sensors):
            cell = cell_names[index % len(cell_names)]
            devices.append(
                Device(
                    device_id=f"SEN-{index + 1:02d}",
                    role="sensor",
                    zone="Operations",
                    process_cell=cell,
                    ip_address=next_ip("Operations"),
                    protocols=ROLE_PROTOCOLS["sensor"],
                    baseline_rate=15.0,
                    criticality="medium",
                )
            )

        for index in range(self.config.actuators):
            cell = cell_names[index % len(cell_names)]
            devices.append(
                Device(
                    device_id=f"ACT-{index + 1:02d}",
                    role="actuator",
                    zone="Operations",
                    process_cell=cell,
                    ip_address=next_ip("Operations"),
                    protocols=ROLE_PROTOCOLS["actuator"],
                    baseline_rate=8.0,
                    criticality="high",
                )
            )

        return devices


class BaselineBehaviorEngine:
    def __init__(self, devices: list[Device], rng: random.Random) -> None:
        self.devices = devices
        self.rng = rng
        self.by_role: dict[str, list[Device]] = defaultdict(list)
        self.by_cell: dict[str, list[Device]] = defaultdict(list)
        for device in devices:
            self.by_role[device.role].append(device)
            self.by_cell[device.process_cell].append(device)
        self.role_weights = {
            "sensor": 4.0,
            "plc": 3.8,
            "gateway": 2.8,
            "hmi": 1.8,
            "actuator": 1.6,
            "historian": 1.0,
        }

        def choose_source(self) -> Device:
            devices = [device for device in self.devices if device.role != "external"]
            weights = [self.role_weights.get(device.role, 1.0) for device in devices]
            return self.rng.choices(devices, weights=weights, k=1)[0]

    def choose_source(self) -> Device:
        devices = [device for device in self.devices if device.role != "external"]
        weights = [self.role_weights.get(device.role, 1.0) for device in devices]
        return self.rng.choices(devices, weights=weights, k=1)[0]

    def choose_target(self, source: Device) -> Device:
        if source.role == "sensor":
            pool = self._devices_in_cell(source.process_cell, ("plc", "gateway"))
        elif source.role == "actuator":
            pool = self._devices_in_cell(source.process_cell, ("plc",))
        elif source.role == "plc":
            pool = self._devices_in_cell(source.process_cell, ("sensor", "actuator", "hmi", "gateway"))
        elif source.role == "hmi":
            pool = self._devices_in_cell(source.process_cell, ("plc", "gateway", "historian"))
        elif source.role == "gateway":
            pool = [device for device in self.devices if device.role in ("plc", "historian", "gateway")]
        else:
            pool = [device for device in self.devices if device.role in ("gateway", "historian")]

        filtered = [device for device in pool if device.device_id != source.device_id]
        if filtered:
            return self.rng.choice(filtered)

        fallback = [device for device in self.devices if device.device_id != source.device_id]
        return self.rng.choice(fallback)

    def _devices_in_cell(self, process_cell: str, roles: tuple[str, ...]) -> list[Device]:
        return [device for device in self.by_cell[process_cell] if device.role in roles]


class ProtocolSimulationEngine:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def simulate(
        self,
        timestamp: datetime,
        source: Device,
        destination: Device,
        record_index: int,
    ) -> TrafficRecord:
        common_protocols = tuple(set(source.protocols) & set(destination.protocols))
        if not common_protocols:
            common_protocols = source.protocols
        protocol = self.rng.choice(tuple(common_protocols))

        service, function_code = self.rng.choice(PROTOCOL_SERVICES[protocol])
        packet_min, packet_max = ROLE_PACKET_SIZE[source.role]
        packet_size = self.rng.randint(packet_min, packet_max)
        latency_ms = round(self.rng.uniform(12, 95) + self._distance_penalty(source, destination), 2)
        jitter_ms = round(self.rng.uniform(0.6, 11.8), 2)
        ttl = self.rng.randint(44, 64)
        retransmissions = 0 if self.rng.random() < 0.88 else self.rng.randint(1, 2)
        traffic_class = self.rng.choice(ROLE_TRAFFIC_CLASS[source.role])
        direction = f"{source.role}->{destination.role}"
        request_rate = round(max(0.4, self.rng.gauss(source.baseline_rate, 1.6)), 2)
        payload_entropy = round(self.rng.uniform(3.1, 5.9), 3)
        burst_index = round(self.rng.uniform(0.04, 0.36), 3)
        protocol_risk = round(self._protocol_risk(protocol, function_code), 3)
        topology_distance = self._topology_distance(source, destination)

        return TrafficRecord(
            timestamp=timestamp,
            source_device=source.device_id,
            source_role=source.role,
            source_ip=source.ip_address,
            destination_device=destination.device_id,
            destination_role=destination.role,
            destination_ip=destination.ip_address,
            protocol=protocol,
            service=service,
            function_code=function_code,
            packet_size=packet_size,
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            ttl=ttl,
            retransmissions=retransmissions,
            direction=direction,
            process_cell=source.process_cell,
            traffic_class=traffic_class,
            session_id=f"SESS-{record_index:06d}",
            request_rate_rps=request_rate,
            payload_entropy=payload_entropy,
            burst_index=burst_index,
            protocol_risk=protocol_risk,
            topology_distance=topology_distance,
        )

    def _distance_penalty(self, source: Device, destination: Device) -> float:
        if source.zone != destination.zone:
            return 18.0
        if source.process_cell != destination.process_cell:
            return 9.0
        return 0.0

    def _topology_distance(self, source: Device, destination: Device) -> int:
        if source.zone != destination.zone:
            return 3
        if source.process_cell != destination.process_cell:
            return 2
        return 1

    def _protocol_risk(self, protocol: str, function_code: str) -> float:
        if protocol == "HTTPS":
            return 0.28
        if protocol == "Modbus TCP" and function_code.startswith("16"):
            return 0.62
        if protocol == "HTTP":
            return 0.41
        return 0.19


class AttackSimulationModule:
    def __init__(self, config: SimulationConfig, devices: list[Device], rng: random.Random) -> None:
        self.config = config
        self.devices = devices
        self.rng = rng
        self.batch_counter = 0
        self.attack_cursor = 0
        self.external_device = Device(
            device_id="EXT-CLOUD-01",
            role="external",
            zone="Untrusted",
            process_cell="External",
            ip_address="198.18.0.44",
            protocols=ROLE_PROTOCOLS["external"],
            baseline_rate=0.0,
            criticality="unknown",
        )

    def generate_attack_records(
        self,
        timestamp: datetime,
        base_index: int,
        recent_records: deque[TrafficRecord],
    ) -> list[TrafficRecord]:
        self.batch_counter += 1
        if not self.config.enabled_attacks:
            return []

        cadence = max(2, int(round(7 - self.config.attack_intensity * 10)))
        should_attack = self.batch_counter % cadence == 0 or self.rng.random() < (self.config.attack_intensity * 0.55)
        if not should_attack:
            return []

        attack_name = self.config.enabled_attacks[self.attack_cursor % len(self.config.enabled_attacks)]
        self.attack_cursor += 1

        if attack_name == "burst_flood":
            return self._burst_flood(timestamp, base_index)
        if attack_name == "rogue_write":
            return self._rogue_write(timestamp, base_index)
        if attack_name == "lateral_scan":
            return self._lateral_scan(timestamp, base_index, recent_records)
        return self._data_exfiltration(timestamp, base_index)

    def _burst_flood(self, timestamp: datetime, base_index: int) -> list[TrafficRecord]:
        gateway = self._pick("gateway")
        plc = self._pick("plc")
        sensor = self._pick("sensor")
        records: list[TrafficRecord] = []
        for offset in range(3):
            records.append(
                TrafficRecord(
                    timestamp=timestamp + timedelta(milliseconds=offset * 18),
                    source_device=sensor.device_id,
                    source_role=sensor.role,
                    source_ip=sensor.ip_address,
                    destination_device=gateway.device_id,
                    destination_role=gateway.role,
                    destination_ip=gateway.ip_address,
                    protocol="MQTT",
                    service="telemetry/flood",
                    function_code="PUBLISH",
                    packet_size=self.rng.randint(1350, 1700),
                    latency_ms=round(self.rng.uniform(110, 220), 2),
                    jitter_ms=round(self.rng.uniform(18, 35), 2),
                    ttl=self.rng.randint(28, 40),
                    retransmissions=self.rng.randint(3, 6),
                    direction=f"{sensor.role}->{gateway.role}",
                    process_cell=sensor.process_cell,
                    traffic_class="flood",
                    session_id=f"SESS-{base_index + offset:06d}",
                    request_rate_rps=round(self.rng.uniform(48, 86), 2),
                    payload_entropy=round(self.rng.uniform(6.4, 7.7), 3),
                    burst_index=round(self.rng.uniform(0.82, 0.97), 3),
                    protocol_risk=0.74,
                    topology_distance=2,
                    state="degraded",
                    attack_name="Burst Flood",
                    attack_stage="impact",
                    label="malicious",
                )
            )

        records.append(
            TrafficRecord(
                timestamp=timestamp + timedelta(milliseconds=75),
                source_device=gateway.device_id,
                source_role=gateway.role,
                source_ip=gateway.ip_address,
                destination_device=plc.device_id,
                destination_role=plc.role,
                destination_ip=plc.ip_address,
                protocol="MQTT",
                service="queue/backpressure",
                function_code="FORWARD",
                packet_size=self.rng.randint(980, 1200),
                latency_ms=round(self.rng.uniform(120, 240), 2),
                jitter_ms=round(self.rng.uniform(10, 28), 2),
                ttl=self.rng.randint(20, 34),
                retransmissions=self.rng.randint(2, 4),
                direction=f"{gateway.role}->{plc.role}",
                process_cell=plc.process_cell,
                traffic_class="congested",
                session_id=f"SESS-{base_index + 3:06d}",
                request_rate_rps=round(self.rng.uniform(26, 42), 2),
                payload_entropy=round(self.rng.uniform(5.9, 7.2), 3),
                burst_index=0.88,
                protocol_risk=0.79,
                topology_distance=2,
                state="degraded",
                attack_name="Burst Flood",
                attack_stage="propagation",
                label="malicious",
            )
        )
        return records

    def _rogue_write(self, timestamp: datetime, base_index: int) -> list[TrafficRecord]:
        hmi = self._pick("hmi")
        plc = self._pick("plc", same_cell=hmi.process_cell)
        return [
            TrafficRecord(
                timestamp=timestamp,
                source_device=hmi.device_id,
                source_role=hmi.role,
                source_ip=hmi.ip_address,
                destination_device=plc.device_id,
                destination_role=plc.role,
                destination_ip=plc.ip_address,
                protocol="Modbus TCP",
                service="write-registers",
                function_code="16 Write Multiple Registers",
                packet_size=self.rng.randint(760, 980),
                latency_ms=round(self.rng.uniform(82, 148), 2),
                jitter_ms=round(self.rng.uniform(7, 16), 2),
                ttl=self.rng.randint(36, 50),
                retransmissions=self.rng.randint(1, 3),
                direction=f"{hmi.role}->{plc.role}",
                process_cell=hmi.process_cell,
                traffic_class="operator",
                session_id=f"SESS-{base_index:06d}",
                request_rate_rps=round(self.rng.uniform(18, 33), 2),
                payload_entropy=round(self.rng.uniform(5.6, 6.9), 3),
                burst_index=round(self.rng.uniform(0.44, 0.69), 3),
                protocol_risk=0.91,
                topology_distance=1,
                state="unsafe",
                attack_name="Rogue PLC Write",
                attack_stage="execution",
                label="malicious",
            )
        ]

    def _lateral_scan(
        self,
        timestamp: datetime,
        base_index: int,
        recent_records: deque[TrafficRecord],
    ) -> list[TrafficRecord]:
        source = self._pick("gateway") if self.rng.random() < 0.5 else self._pick("hmi")
        targets = self.rng.sample([device for device in self.devices if device.role in ("plc", "hmi", "historian")], k=3)
        records: list[TrafficRecord] = []
        for offset, target in enumerate(targets):
            records.append(
                TrafficRecord(
                    timestamp=timestamp + timedelta(milliseconds=offset * 12),
                    source_device=source.device_id,
                    source_role=source.role,
                    source_ip=source.ip_address,
                    destination_device=target.device_id,
                    destination_role=target.role,
                    destination_ip=target.ip_address,
                    protocol="HTTP",
                    service="inventory/scan",
                    function_code="TCP SYN",
                    packet_size=self.rng.randint(96, 160),
                    latency_ms=round(self.rng.uniform(40, 88), 2),
                    jitter_ms=round(self.rng.uniform(2, 9), 2),
                    ttl=self.rng.randint(41, 56),
                    retransmissions=0,
                    direction=f"{source.role}->{target.role}",
                    process_cell=source.process_cell,
                    traffic_class="recon",
                    session_id=f"SESS-{base_index + offset:06d}",
                    request_rate_rps=round(self.rng.uniform(22, 35), 2),
                    payload_entropy=round(self.rng.uniform(4.8, 5.7), 3),
                    burst_index=round(self.rng.uniform(0.58, 0.78), 3),
                    protocol_risk=0.83,
                    topology_distance=2 if source.process_cell != target.process_cell else 1,
                    state="recon",
                    attack_name="Lateral Scan",
                    attack_stage="reconnaissance",
                    label="malicious",
                )
            )
        return records

    def _data_exfiltration(self, timestamp: datetime, base_index: int) -> list[TrafficRecord]:
        historian = self._pick("historian")
        return [
            TrafficRecord(
                timestamp=timestamp,
                source_device=historian.device_id,
                source_role=historian.role,
                source_ip=historian.ip_address,
                destination_device=self.external_device.device_id,
                destination_role=self.external_device.role,
                destination_ip=self.external_device.ip_address,
                protocol="HTTPS",
                service="backup/export",
                function_code="POST",
                packet_size=self.rng.randint(1400, 1750),
                latency_ms=round(self.rng.uniform(150, 320), 2),
                jitter_ms=round(self.rng.uniform(14, 28), 2),
                ttl=self.rng.randint(21, 38),
                retransmissions=self.rng.randint(2, 5),
                direction=f"{historian.role}->{self.external_device.role}",
                process_cell=historian.process_cell,
                traffic_class="egress",
                session_id=f"SESS-{base_index:06d}",
                request_rate_rps=round(self.rng.uniform(8, 14), 2),
                payload_entropy=round(self.rng.uniform(7.1, 7.9), 3),
                burst_index=round(self.rng.uniform(0.51, 0.72), 3),
                protocol_risk=0.95,
                topology_distance=4,
                state="compromised",
                attack_name="Data Exfiltration",
                attack_stage="exfiltration",
                label="malicious",
            )
        ]

    def _pick(self, role: str, same_cell: str | None = None) -> Device:
        pool = [device for device in self.devices if device.role == role]
        if same_cell is not None:
            same_cell_pool = [device for device in pool if device.process_cell == same_cell]
            if same_cell_pool:
                pool = same_cell_pool
        return self.rng.choice(pool)


class AnomalyDetectionLayer:
    def __init__(self) -> None:
        self.unique_destinations: dict[str, set[str]] = defaultdict(set)

    def annotate(self, record: TrafficRecord, recent_records: deque[TrafficRecord]) -> None:
        score = 0.08 + record.protocol_risk * 0.18 + min(record.burst_index, 1.0) * 0.12

        if record.packet_size > 1200:
            score += 0.18
        if record.request_rate_rps > 18:
            score += 0.12
        if record.destination_role == "external":
            score += 0.24
        if "Write" in record.function_code or record.function_code in {"POST", "PUT"}:
            score += 0.08
        if record.retransmissions > 2:
            score += 0.07
        if record.state not in {"normal", "stable"}:
            score += 0.1
        if record.label == "malicious":
            score += 0.32
        if record.attack_name == "Lateral Scan":
            score += 0.16

        source_key = f"{record.source_device}:{record.protocol}"
        self.unique_destinations[source_key].add(record.destination_device)
        if len(self.unique_destinations[source_key]) > 2:
            score += 0.14

        for previous in recent_records:
            same_source = previous.source_device == record.source_device
            close_in_time = abs((record.timestamp - previous.timestamp).total_seconds()) < 2.0
            if same_source and close_in_time and previous.destination_device != record.destination_device:
                score += 0.03

        score = max(0.0, min(score, 0.99))
        record.anomaly_score = round(score, 3)

        if score >= 0.72:
            record.anomaly_label = "critical"
        elif score >= 0.48:
            record.anomaly_label = "suspicious"
        else:
            record.anomaly_label = "normal"

        if record.label != "malicious" and record.anomaly_label != "normal":
            record.label = "anomalous"


class TrafficDatasetGenerator:
    def __init__(self) -> None:
        self.records: list[TrafficRecord] = []

    def add(self, records: list[TrafficRecord]) -> None:
        self.records.extend(records)

    def export_csv(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer: csv.DictWriter[str] | None = None
            for record in self.records:
                row = record.to_dict()
                if writer is None:
                    writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
                    writer.writeheader()
                writer.writerow(row)
        return path


class IIoTSimulationFramework:
    def __init__(self, config: SimulationConfig, output_directory: str | Path | None = None) -> None:
        self.config = config
        self.output_directory = Path(output_directory or Path.cwd())
        self.rng = random.Random(config.seed)
        self.topology_generator = NetworkTopologyGenerator(config, self.rng)
        self.devices = self.topology_generator.generate()
        self.baseline_engine = BaselineBehaviorEngine(self.devices, self.rng)
        self.protocol_engine = ProtocolSimulationEngine(self.rng)
        self.attack_engine = AttackSimulationModule(config, self.devices, self.rng)
        self.anomaly_layer = AnomalyDetectionLayer()
        self.dataset = TrafficDatasetGenerator()
        self.snapshot = SimulationSnapshot()
        self.recent_records: deque[TrafficRecord] = deque(maxlen=60)
        self.current_time = datetime.now().replace(microsecond=0)
        self.record_counter = 0
        self.initial_records: list[TrafficRecord] = []

    def generate_initial_records(self, count: int = 36) -> list[TrafficRecord]:
        records = self._generate_base_records(count)
        self._finalize_records(records)
        self.dataset.add(records)
        self.initial_records = list(records)
        return records

    def generate_batch(self, batch_size: int | None = None) -> list[TrafficRecord]:
        normal_batch_size = batch_size or self.config.batch_size
        records = self._generate_base_records(normal_batch_size)
        attack_records = self.attack_engine.generate_attack_records(
            self.current_time,
            self.record_counter + 1,
            self.recent_records,
        )
        records.extend(attack_records)
        records.sort(key=lambda record: record.timestamp)
        self._finalize_records(records)
        self.dataset.add(records)
        return records

    def export_dataset(self, filename: str = "realistic_iiot_traffic.csv") -> Path:
        return self.dataset.export_csv(self.output_directory / filename)

    def export_initial_snapshot(self, filename: str = "initially_generated_records.csv") -> Path:
        path = self.output_directory / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer: csv.DictWriter[str] | None = None
            for record in self.initial_records:
                row = record.to_dict()
                if writer is None:
                    writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
                    writer.writeheader()
                writer.writerow(row)
        return path

    def topology_summary(self) -> list[str]:
        grouped: dict[str, list[Device]] = defaultdict(list)
        for device in self.devices:
            grouped[device.process_cell].append(device)

        summary: list[str] = []
        for cell in sorted(grouped):
            summary.append(f"{cell}")
            for device in sorted(grouped[cell], key=lambda item: (item.role, item.device_id)):
                protocols = ", ".join(device.protocols)
                summary.append(f"  {device.device_id:<9} {device.role:<10} {device.ip_address:<14} {protocols}")
        return summary

    def _generate_base_records(self, count: int) -> list[TrafficRecord]:
        records: list[TrafficRecord] = []
        for _ in range(count):
            self.record_counter += 1
            source = self.baseline_engine.choose_source()
            destination = self.baseline_engine.choose_target(source)
            self.current_time += timedelta(milliseconds=self.rng.randint(120, 960))
            record = self.protocol_engine.simulate(
                timestamp=self.current_time,
                source=source,
                destination=destination,
                record_index=self.record_counter,
            )
            records.append(record)
        return records

    def _finalize_records(self, records: list[TrafficRecord]) -> None:
        for record in records:
            self.anomaly_layer.annotate(record, self.recent_records)
            self.recent_records.append(record)
            self._update_snapshot(record)

    def _update_snapshot(self, record: TrafficRecord) -> None:
        self.snapshot.total_records += 1
        if record.label == "malicious":
            self.snapshot.malicious_records += 1
        elif record.anomaly_label != "normal":
            self.snapshot.suspicious_records += 1
        else:
            self.snapshot.normal_records += 1

        self.snapshot.last_protocol = record.protocol
        if record.attack_name:
            self.snapshot.active_attack = record.attack_name
        self.snapshot.protocol_counts[record.protocol] = self.snapshot.protocol_counts.get(record.protocol, 0) + 1

        cumulative_score = self.snapshot.average_anomaly_score * (self.snapshot.total_records - 1)
        self.snapshot.average_anomaly_score = round(
            (cumulative_score + record.anomaly_score) / self.snapshot.total_records,
            3,
        )

        if record.anomaly_label != "normal" or record.label == "malicious":
            event = (
                f"{record.timestamp.strftime('%H:%M:%S')} | {record.source_device} -> "
                f"{record.destination_device} | {record.protocol} | {record.attack_name or record.anomaly_label}"
            )
            self.snapshot.alert_log.append(event)
            self.snapshot.alert_log = self.snapshot.alert_log[-50:]
