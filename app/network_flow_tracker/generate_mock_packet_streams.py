from pathlib import Path
import csv


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

    packets = [
        # TCP Stream A (first segment)
        ("1.0", "10.0.0.1", "50000", "142.250.72.14", "443", "tcp", "TLSv1.3", "120"),
        ("1.2", "142.250.72.14", "443", "10.0.0.1", "50000", "tcp", "TLSv1.3", "130"),

        # UDP Stream B (continuous)
        ("2.0", "10.0.0.2", "51000", "104.18.32.1", "443", "udp", "QUIC", "90"),
        ("2.2", "104.18.32.1", "443", "10.0.0.2", "51000", "udp", "QUIC", "95"),

        # Interleaved TCP Stream A (still same stream)
        ("3.0", "10.0.0.1", "50000", "142.250.72.14", "443", "tcp", "TLSv1.3", "125"),

        # Idle gap > 30s → TCP Stream A must split
        ("35.0", "10.0.0.1", "50000", "142.250.72.14", "443", "tcp", "TLSv1.3", "140"),

        # New independent TCP Stream C
        ("36.0", "10.0.0.3", "52000", "93.184.216.34", "443", "tcp", "TLSv1.3", "110"),
        ("36.3", "93.184.216.34", "443", "10.0.0.3", "52000", "tcp", "TLSv1.3", "115"),
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(packets)

    print(f"[MOCK] Finite mock packet CSV generated at:")
    print(csv_path)


if __name__ == "__main__":
    output_csv = Path("D:/FYP_DEV/app/network_flow_tracker/live_https_v1.csv")
    generate_mock_csv(output_csv)
