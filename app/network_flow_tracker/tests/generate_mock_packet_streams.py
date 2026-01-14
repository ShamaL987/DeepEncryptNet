from pathlib import Path
import csv
import time


def generate_mock_csv(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "timestamp",
        "src_ip",
        "src_port",
        "dst_ip",
        "dst_port",
        "transport",
        "app_protocol",
        "packet_length",
    ]

    base_ts = time.time()

    packets = [
        # TCP Stream A (first segment)
        (base_ts + 1.0, "10.0.0.1", "50000", "142.250.72.14", "443", "tcp", "TLSv1.3", "120"),
        (base_ts + 1.2, "142.250.72.14", "443", "10.0.0.1", "50000", "tcp", "TLSv1.3", "130"),

        # UDP Stream B
        (base_ts + 2.0, "10.0.0.2", "51000", "104.18.32.1", "443", "udp", "QUIC", "90"),
        (base_ts + 2.2, "104.18.32.1", "443", "10.0.0.2", "51000", "udp", "QUIC", "95"),

        # Interleaved TCP Stream A (same stream)
        (base_ts + 3.0, "10.0.0.1", "50000", "142.250.72.14", "443", "tcp", "TLSv1.3", "125"),

        # Idle gap > 30 seconds → TCP Stream A splits
        (base_ts + 35.0, "10.0.0.1", "50000", "142.250.72.14", "443", "tcp", "TLSv1.3", "140"),

        # New TCP Stream C
        (base_ts + 36.0, "10.0.0.3", "52000", "93.184.216.34", "443", "tcp", "TLSv1.3", "110"),
        (base_ts + 36.3, "93.184.216.34", "443", "10.0.0.3", "52000", "tcp", "TLSv1.3", "115"),
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in packets:
            writer.writerow([f"{row[0]:.6f}", *row[1:]])

    print("[MOCK] Finite mock packet CSV generated")
    print(csv_path)


if __name__ == "__main__":
    output_csv = Path("D:/FYP_DEV/app/network_flow_tracker/live_https_v1.csv")
    generate_mock_csv(output_csv)
