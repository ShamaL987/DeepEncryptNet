from pathlib import Path

from app.network_flow_tracker.new_v1 import PacketStreamDivider


def main() -> None:
    tracker_dir = Path("D:/FYP_DEV/tracker-exe")
    working_dir = Path.cwd()

    divider = PacketStreamDivider(
        packet_csv=working_dir / "live_https_v1.csv",
        output_dir=working_dir / "streams",
        offset_file=working_dir / "offset.json",
        start_mode="replay",  # "replay" or "live"
        idle_timeout_sec=30.0,
        poll_interval_sec=1.0,
    )

    divider.run()


if __name__ == "__main__":
    main()
