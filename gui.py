from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from models import SimulationConfig, SimulationSnapshot, TrafficRecord
from simulator import ATTACK_DISPLAY_NAMES, IIoTSimulationFramework


class EnhancedModernGUI:
    def __init__(self, output_directory: str | Path | None = None) -> None:
        self.output_directory = Path(output_directory or Path.cwd())
        self.root = tk.Tk()
        self.root.title("IIoT Traffic Dataset Simulator")
        self.root.geometry("1480x920")
        self.root.minsize(1260, 820)
        self.root.configure(bg="#0e1420")

        self._apply_theme()
        self._build_variables()

        self.framework: IIoTSimulationFramework | None = None
        self.simulation_thread: threading.Thread | None = None
        self.ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.running = False
        self.paused = False

        self.metric_labels: dict[str, ttk.Label] = {}
        self.protocol_bar_labels: list[ttk.Label] = []

        self._build_layout()
        self._reset_framework(announce=False)
        self.root.after(150, self._process_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self) -> None:
        self.root.mainloop()

    def _apply_theme(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#0e1420", foreground="#e6edf5", fieldbackground="#111b2b")
        style.configure("TFrame", background="#0e1420")
        style.configure("Card.TFrame", background="#111b2b")
        style.configure("Header.TLabel", background="#0e1420", foreground="#f4f7fb", font=("Helvetica", 24, "bold"))
        style.configure("Subhead.TLabel", background="#0e1420", foreground="#93a5be", font=("Helvetica", 11))
        style.configure("Section.TLabel", background="#111b2b", foreground="#f4f7fb", font=("Helvetica", 13, "bold"))
        style.configure("Body.TLabel", background="#111b2b", foreground="#d4deea", font=("Helvetica", 10))
        style.configure("MetricValue.TLabel", background="#111b2b", foreground="#f4f7fb", font=("Helvetica", 22, "bold"))
        style.configure("MetricCaption.TLabel", background="#111b2b", foreground="#8ea4c0", font=("Helvetica", 10))
        style.configure("Accent.TButton", background="#0ea5a2", foreground="#071017", padding=10, borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#14b8b2")])
        style.configure("Muted.TButton", background="#1e293b", foreground="#dbe7f5", padding=10, borderwidth=0)
        style.map("Muted.TButton", background=[("active", "#253347")])
        style.configure("Treeview", background="#111b2b", fieldbackground="#111b2b", foreground="#dde8f4", rowheight=28)
        style.configure("Treeview.Heading", background="#162235", foreground="#dde8f4", font=("Helvetica", 10, "bold"))
        style.map("Treeview", background=[("selected", "#18456a")])
        style.configure("TLabelframe", background="#111b2b", foreground="#f4f7fb")
        style.configure("TLabelframe.Label", background="#111b2b", foreground="#f4f7fb", font=("Helvetica", 12, "bold"))
        style.configure("TCheckbutton", background="#111b2b", foreground="#d4deea")
        style.configure("TSpinbox", fieldbackground="#0c1220", foreground="#e6edf5")

    def _build_variables(self) -> None:
        self.sensor_var = tk.IntVar(value=12)
        self.actuator_var = tk.IntVar(value=6)
        self.plc_var = tk.IntVar(value=3)
        self.hmi_var = tk.IntVar(value=2)
        self.gateway_var = tk.IntVar(value=1)
        self.historian_var = tk.IntVar(value=1)
        self.batch_var = tk.IntVar(value=10)
        self.interval_var = tk.DoubleVar(value=0.9)
        self.attack_intensity_var = tk.DoubleVar(value=0.32)
        self.seed_var = tk.IntVar(value=42)

        self.attack_vars: dict[str, tk.BooleanVar] = {
            attack: tk.BooleanVar(value=True) for attack in ATTACK_DISPLAY_NAMES
        }

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True, padx=18, pady=18)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(1, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        title_block = ttk.Frame(header)
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="Realistic IIoT Traffic Simulation Framework", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            title_block,
            text="Topology generation, protocol emulation, attack injection, anomaly scoring, and dataset export.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        button_bar = ttk.Frame(header)
        button_bar.grid(row=0, column=1, sticky="e")
        ttk.Button(button_bar, text="Start", style="Accent.TButton", command=self.start_background_traffic).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Pause", style="Muted.TButton", command=self.toggle_pause).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Reset", style="Muted.TButton", command=self.reset_simulation).pack(side="left", padx=4)
        ttk.Button(button_bar, text="Export CSV", style="Muted.TButton", command=self.export_dataset).pack(side="left", padx=4)

        sidebar = ttk.Frame(outer, style="Card.TFrame", padding=16)
        sidebar.grid(row=1, column=0, sticky="nsw")
        sidebar.configure(width=320)

        content = ttk.Frame(outer)
        content.grid(row=1, column=1, sticky="nsew", padx=(16, 0))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)
        content.rowconfigure(2, weight=1)

        self._build_sidebar(sidebar)
        self._build_metrics(content)
        self._build_traffic_table(content)
        self._build_bottom_panels(content)

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Simulation Controls", style="Section.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Tune the topology and the live batch cadence before starting.", style="Body.TLabel").pack(
            anchor="w",
            pady=(4, 16),
        )

        topology_frame = ttk.LabelFrame(parent, text="Topology")
        topology_frame.pack(fill="x", pady=(0, 14))
        self._make_spinner(topology_frame, "Sensors", self.sensor_var).pack(fill="x", pady=4)
        self._make_spinner(topology_frame, "Actuators", self.actuator_var).pack(fill="x", pady=4)
        self._make_spinner(topology_frame, "PLCs", self.plc_var).pack(fill="x", pady=4)
        self._make_spinner(topology_frame, "HMIs", self.hmi_var).pack(fill="x", pady=4)
        self._make_spinner(topology_frame, "Gateways", self.gateway_var).pack(fill="x", pady=4)
        self._make_spinner(topology_frame, "Historians", self.historian_var).pack(fill="x", pady=4)

        runtime_frame = ttk.LabelFrame(parent, text="Runtime")
        runtime_frame.pack(fill="x", pady=(0, 14))
        self._make_spinner(runtime_frame, "Batch size", self.batch_var, minimum=3, maximum=40).pack(fill="x", pady=4)
        self._make_spinner(runtime_frame, "Interval (s)", self.interval_var, minimum=0.2, maximum=5.0, increment=0.1).pack(
            fill="x",
            pady=4,
        )
        self._make_spinner(runtime_frame, "Attack intensity", self.attack_intensity_var, minimum=0.05, maximum=0.95, increment=0.01).pack(
            fill="x",
            pady=4,
        )
        self._make_spinner(runtime_frame, "Seed", self.seed_var, minimum=1, maximum=9999).pack(fill="x", pady=4)

        attack_frame = ttk.LabelFrame(parent, text="Attack Modules")
        attack_frame.pack(fill="x", pady=(0, 14))
        for attack_key, label in ATTACK_DISPLAY_NAMES.items():
            ttk.Checkbutton(attack_frame, text=label, variable=self.attack_vars[attack_key]).pack(anchor="w", pady=2, padx=4)

        note = ttk.Label(
            parent,
            text="The simulator maps directly to the PDF stages: topology, baseline behavior, protocol simulation, attacks, feature extraction, anomaly detection, and final dataset generation.",
            style="Body.TLabel",
            wraplength=280,
            justify="left",
        )
        note.pack(anchor="w", pady=(8, 0))

    def _make_spinner(
        self,
        parent: ttk.LabelFrame,
        label: str,
        variable: tk.Variable,
        minimum: float = 1,
        maximum: float = 99,
        increment: float = 1,
    ) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=label, style="Body.TLabel").grid(row=0, column=0, sticky="w")
        spin = ttk.Spinbox(frame, from_=minimum, to=maximum, increment=increment, textvariable=variable, width=10)
        spin.grid(row=0, column=1, sticky="e")
        return frame

    def _build_metrics(self, parent: ttk.Frame) -> None:
        metric_row = ttk.Frame(parent)
        metric_row.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        for index in range(5):
            metric_row.columnconfigure(index, weight=1)

        cards = [
            ("total_records", "Total Records"),
            ("normal_records", "Normal"),
            ("suspicious_records", "Suspicious"),
            ("malicious_records", "Malicious"),
            ("average_anomaly_score", "Avg Score"),
        ]

        for index, (key, label) in enumerate(cards):
            card = ttk.Frame(metric_row, style="Card.TFrame", padding=14)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 10, 0))
            ttk.Label(card, text=label, style="MetricCaption.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="0", style="MetricValue.TLabel")
            value.pack(anchor="w", pady=(8, 0))
            self.metric_labels[key] = value

    def _build_traffic_table(self, parent: ttk.Frame) -> None:
        table_card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        table_card.grid(row=1, column=0, sticky="nsew", pady=(0, 14))
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(1, weight=1)

        header = ttk.Frame(table_card, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Live Traffic Stream", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(header, text="Idle", style="Body.TLabel")
        self.status_label.grid(row=0, column=1, sticky="e")

        columns = (
            "timestamp",
            "source",
            "protocol",
            "service",
            "destination",
            "size",
            "score",
            "label",
        )
        self.traffic_table = ttk.Treeview(table_card, columns=columns, show="headings")
        headings = {
            "timestamp": "Timestamp",
            "source": "Source",
            "protocol": "Protocol",
            "service": "Service",
            "destination": "Destination",
            "size": "Bytes",
            "score": "Score",
            "label": "Label",
        }
        widths = {
            "timestamp": 160,
            "source": 110,
            "protocol": 110,
            "service": 170,
            "destination": 110,
            "size": 90,
            "score": 80,
            "label": 90,
        }
        for column in columns:
            self.traffic_table.heading(column, text=headings[column])
            self.traffic_table.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.traffic_table.yview)
        self.traffic_table.configure(yscrollcommand=scrollbar.set)
        self.traffic_table.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

    def _build_bottom_panels(self, parent: ttk.Frame) -> None:
        bottom = ttk.Frame(parent)
        bottom.grid(row=2, column=0, sticky="nsew")
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)
        bottom.columnconfigure(2, weight=1)
        bottom.rowconfigure(0, weight=1)

        topology_card = ttk.Frame(bottom, style="Card.TFrame", padding=14)
        topology_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ttk.Label(topology_card, text="Topology Map", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.topology_text = tk.Text(
            topology_card,
            bg="#0d1727",
            fg="#d6e2ef",
            relief="flat",
            wrap="none",
            height=16,
            font=("Menlo", 10),
        )
        self.topology_text.pack(fill="both", expand=True)

        alerts_card = ttk.Frame(bottom, style="Card.TFrame", padding=14)
        alerts_card.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        ttk.Label(alerts_card, text="Alert Feed", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.alert_text = tk.Text(
            alerts_card,
            bg="#0d1727",
            fg="#d6e2ef",
            relief="flat",
            wrap="word",
            height=16,
            font=("Menlo", 10),
        )
        self.alert_text.pack(fill="both", expand=True)

        chart_card = ttk.Frame(bottom, style="Card.TFrame", padding=14)
        chart_card.grid(row=0, column=2, sticky="nsew")
        ttk.Label(chart_card, text="Protocol Mix", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.protocol_chart = tk.Canvas(chart_card, bg="#0d1727", highlightthickness=0, height=300)
        self.protocol_chart.pack(fill="both", expand=True)

    def start_background_traffic(self) -> None:
        if not self.running:
            self._reset_framework()
        if self.running and not self.paused:
            return
        if self.framework is None:
            self._reset_framework()

        self.running = True
        self.paused = False
        self.status_label.configure(text="Streaming")

        if self.simulation_thread is None or not self.simulation_thread.is_alive():
            self.simulation_thread = threading.Thread(target=self._background_worker, daemon=True)
            self.simulation_thread.start()

    def toggle_pause(self) -> None:
        if not self.running:
            return
        self.paused = not self.paused
        self.status_label.configure(text="Paused" if self.paused else "Streaming")

    def reset_simulation(self) -> None:
        self.running = False
        self.paused = False
        self._reset_framework()

    def export_dataset(self) -> None:
        if self.framework is None:
            return
        default_path = self.output_directory / "realistic_iiot_traffic.csv"
        selected = filedialog.asksaveasfilename(
            title="Export IIoT Dataset",
            defaultextension=".csv",
            initialfile=default_path.name,
            initialdir=str(default_path.parent),
            filetypes=[("CSV", "*.csv")],
        )
        if not selected:
            return

        path = self.framework.dataset.export_csv(Path(selected))
        messagebox.showinfo("Dataset Exported", f"Saved {len(self.framework.dataset.records)} rows to:\n{path}")

    def _background_worker(self) -> None:
        while True:
            if not self.running:
                time.sleep(0.1)
                continue
            if self.paused:
                time.sleep(0.15)
                continue
            if self.framework is None:
                time.sleep(0.1)
                continue

            batch = self.framework.generate_batch(self.batch_var.get())
            self.framework.export_dataset("realistic_iiot_traffic.csv")
            self.ui_queue.put(("batch", batch))
            time.sleep(max(0.15, self.interval_var.get()))

    def _reset_framework(self, announce: bool = True) -> None:
        config = self._current_config()
        self.framework = IIoTSimulationFramework(config=config, output_directory=self.output_directory)

        for child in self.traffic_table.get_children():
            self.traffic_table.delete(child)
        self.alert_text.delete("1.0", "end")
        self.topology_text.delete("1.0", "end")

        initial_records = self.framework.generate_initial_records(36)
        self.framework.export_initial_snapshot("initially_generated_records.csv")
        self.framework.export_dataset("realistic_iiot_traffic.csv")

        for line in self.framework.topology_summary():
            self.topology_text.insert("end", f"{line}\n")

        self._append_records(initial_records[-14:])
        self._render_snapshot(self.framework.snapshot)
        self._draw_protocol_chart(self.framework.snapshot.protocol_counts)
        self.status_label.configure(text="Ready")

        if announce:
            self.alert_text.insert(
                "end",
                "Framework reset. Initial baseline traffic generated and exported to initially_generated_records.csv.\n",
            )
            self.alert_text.see("end")

    def _current_config(self) -> SimulationConfig:
        enabled_attacks = tuple(
            attack_name for attack_name, variable in self.attack_vars.items() if variable.get()
        )
        return SimulationConfig(
            sensors=max(1, self.sensor_var.get()),
            actuators=max(1, self.actuator_var.get()),
            plcs=max(1, self.plc_var.get()),
            hmis=max(1, self.hmi_var.get()),
            gateways=max(1, self.gateway_var.get()),
            historians=max(1, self.historian_var.get()),
            batch_size=max(1, self.batch_var.get()),
            interval_seconds=max(0.2, float(self.interval_var.get())),
            attack_intensity=min(max(float(self.attack_intensity_var.get()), 0.05), 0.95),
            seed=max(1, self.seed_var.get()),
            enabled_attacks=enabled_attacks,
        )

    def _process_queue(self) -> None:
        while True:
            try:
                kind, payload = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "batch" and self.framework is not None:
                records = payload
                assert isinstance(records, list)
                self._append_records(records)
                self._render_snapshot(self.framework.snapshot)
                self._draw_protocol_chart(self.framework.snapshot.protocol_counts)
                self._render_alerts(self.framework.snapshot.alert_log[-10:])

        self.root.after(150, self._process_queue)

    def _append_records(self, records: list[TrafficRecord]) -> None:
        for record in records:
            score = f"{record.anomaly_score:.3f}"
            label = "malicious" if record.label == "malicious" else record.anomaly_label
            self.traffic_table.insert(
                "",
                "end",
                values=(
                    record.timestamp.strftime("%H:%M:%S.%f")[:-3],
                    record.source_device,
                    record.protocol,
                    record.service,
                    record.destination_device,
                    record.packet_size,
                    score,
                    label,
                ),
            )

        children = self.traffic_table.get_children()
        for item in children[:-90]:
            self.traffic_table.delete(item)

        if children:
            self.traffic_table.yview_moveto(1.0)

    def _render_snapshot(self, snapshot: SimulationSnapshot) -> None:
        self.metric_labels["total_records"].configure(text=str(snapshot.total_records))
        self.metric_labels["normal_records"].configure(text=str(snapshot.normal_records))
        self.metric_labels["suspicious_records"].configure(text=str(snapshot.suspicious_records))
        self.metric_labels["malicious_records"].configure(text=str(snapshot.malicious_records))
        self.metric_labels["average_anomaly_score"].configure(text=f"{snapshot.average_anomaly_score:.3f}")
        self.status_label.configure(text=f"{snapshot.last_protocol} | Active attack: {snapshot.active_attack}")

    def _render_alerts(self, alerts: list[str]) -> None:
        self.alert_text.delete("1.0", "end")
        if not alerts:
            self.alert_text.insert("end", "No active anomalies detected.\n")
            return
        for alert in alerts:
            self.alert_text.insert("end", f"{alert}\n")
        self.alert_text.see("end")

    def _draw_protocol_chart(self, counts: dict[str, int]) -> None:
        self.protocol_chart.delete("all")
        if not counts:
            return

        width = max(320, self.protocol_chart.winfo_width())
        bar_height = 28
        gap = 12
        max_value = max(counts.values())
        colors = ["#0ea5a2", "#1d4ed8", "#f59e0b", "#e11d48", "#22c55e", "#8b5cf6"]

        for index, (protocol, value) in enumerate(sorted(counts.items(), key=lambda item: item[1], reverse=True)):
            top = 16 + index * (bar_height + gap)
            bar_width = int((width - 160) * (value / max_value))
            color = colors[index % len(colors)]
            self.protocol_chart.create_text(12, top + 14, text=protocol, anchor="w", fill="#dbe7f5", font=("Helvetica", 11))
            self.protocol_chart.create_rectangle(130, top, 130 + bar_width, top + bar_height, fill=color, width=0)
            self.protocol_chart.create_text(140 + bar_width, top + 14, text=str(value), anchor="w", fill="#9ec0da", font=("Helvetica", 10))

    def _on_close(self) -> None:
        self.running = False
        self.root.destroy()
