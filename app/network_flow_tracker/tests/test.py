from pathlib import Path

from app.network_flow_tracker.flow_extractor import PacketStreamDivider


def main() -> None:
    working_dir = Path.cwd()

    divider = PacketStreamDivider(
        packet_csv=working_dir / "live_https_v1.csv",
        output_dir=working_dir / "streams",
        extract_features=False,
        prediction_queue=None,
        idle_timeout_sec=10.0,
        max_packets=100,
        max_duration_sec=20.0,
    )

    result = divider.run(
        stop_event=None,
        batch_id="test_batch_001",
    )

    print("Divider result:")
    print(result)


if __name__ == "__main__":
    main()