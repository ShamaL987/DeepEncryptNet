from pathlib import Path

from app.network_flow_tracker.new_v1 import PacketStreamDivider


def main() -> None:
    base_dir = Path("tracker-exe")

    packet_csv = base_dir / "captures" / "live_https.csv"
    output_dir = base_dir / "streams"
    offset_file = base_dir / "offset.json"

    divider = PacketStreamDivider(
        packet_csv=packet_csv,
        output_dir=output_dir,
        offset_store=offset_file,
        idle_timeout_sec=30.0,
        poll_interval_sec=1.0,
    )

    divider.run()


if __name__ == "__main__":
    main()
