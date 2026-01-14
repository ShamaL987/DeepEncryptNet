from pathlib import Path

from app.network_flow_tracker.flow_extractor import PacketStreamDivider


def main() -> None:
    tracker_dir = Path("D:/FYP_DEV/tracker-exe")
    working_dir = Path.cwd()

    divider = PacketStreamDivider(
        packet_csv=working_dir / "live_https_v1.csv",
        output_dir=working_dir / "streams",
        offset_file=working_dir / "offset.json",
        start_mode="live",  # "replay" or "live"
        idle_timeout_sec=10.0,
        poll_interval_sec=1.0,
        extract_features=True,
    )

    divider.run()


if __name__ == "__main__":
    main()
