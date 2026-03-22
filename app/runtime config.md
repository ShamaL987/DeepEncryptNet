## Notes

- `ready_dir` → new batch CSV files come here
- `processing_dir` → batch file is moved here while processing
- `processed_dir` → processed batch file is moved here if saving is enabled
- `streams_dir` → unique packet stream CSV files are saved here

- `save_processed_batch_file` → keep or delete processed batch CSV
- `save_stream_files` → keep or delete unique stream CSV files

- `idle_timeout_sec` → finalize stream if idle too long
- `max_packets` → finalize stream if packet count limit reached
- `max_duration_sec` → finalize stream if duration limit reached

- `auto_start` → start daemon automatically or not
- `mode` → running mode
- `poll_interval_sec` → how often to check for new batch files

- `enable_stats` → extract features or not
- `feature_pipeline` → feature pipeline name

- `timeout` → wait time after processing one batch