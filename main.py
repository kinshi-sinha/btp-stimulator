from __future__ import annotations

import argparse
from pathlib import Path

from gui import EnhancedModernGUI
from simulator import IIoTSimulationFramework
from models import SimulationConfig


def run_headless(args: argparse.Namespace) -> None:
    config = SimulationConfig(
        sensors=args.sensors,
        actuators=args.actuators,
        plcs=args.plcs,
        hmis=args.hmis,
        gateways=args.gateways,
        historians=args.historians,
        batch_size=args.batch_size,
        interval_seconds=args.interval_seconds,
        attack_intensity=args.attack_intensity,
        seed=args.seed,
    )

    framework = IIoTSimulationFramework(config=config, output_directory=Path(args.output).parent)
    framework.generate_initial_records(args.initial_records)

    while framework.snapshot.total_records < args.records:
        framework.generate_batch(args.batch_size)

    output_path = framework.dataset.export_csv(Path(args.output))
    framework.export_initial_snapshot("initially_generated_records.csv")

    print(f"Generated {framework.snapshot.total_records} records")
    print(f"Normal records: {framework.snapshot.normal_records}")
    print(f"Suspicious records: {framework.snapshot.suspicious_records}")
    print(f"Malicious records: {framework.snapshot.malicious_records}")
    print(f"Average anomaly score: {framework.snapshot.average_anomaly_score:.3f}")
    print(f"Dataset saved to: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IIoT traffic simulator")
    parser.add_argument("--headless", action="store_true", help="Run dataset generation without starting the GUI")
    parser.add_argument("--records", type=int, default=220, help="Total number of records to generate in headless mode")
    parser.add_argument("--initial-records", type=int, default=36, help="Baseline records generated before live streaming")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--interval-seconds", type=float, default=0.9)
    parser.add_argument("--attack-intensity", type=float, default=0.32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sensors", type=int, default=12)
    parser.add_argument("--actuators", type=int, default=6)
    parser.add_argument("--plcs", type=int, default=3)
    parser.add_argument("--hmis", type=int, default=2)
    parser.add_argument("--gateways", type=int, default=1)
    parser.add_argument("--historians", type=int, default=1)
    parser.add_argument("--output", default="realistic_iiot_traffic.csv")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.headless:
        run_headless(args)
        return

    app = EnhancedModernGUI(output_directory=Path.cwd())
    app.run()


if __name__ == "__main__":
    main()
