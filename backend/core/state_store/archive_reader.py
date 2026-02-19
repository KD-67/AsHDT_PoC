import json
import os
import logging
from datetime import datetime, timezone


# Module-level logger. Using __name__ means log messages will be prefixed with
# 'backend.core.state_store.archive_reader', making it easy to filter in output.
logger = logging.getLogger(__name__)


def read_timeseries(
    archive_root: str,
    subject_id: str,
    module_id: str,
    marker_id: str,
    from_time: datetime,
    to_time: datetime,
) -> list[dict]:
    """
    Reads data point files from the archive folder hierarchy for a given subject,
    module, and marker, filtered to a specific time range.

    Returns a list of dicts sorted chronologically. Each dict contains all fields
    from the original data point JSON file, plus a 'parsed_timestamp' key holding
    the timestamp as a Python datetime object (needed by the trajectory computer).

    Raises FileNotFoundError if index.json does not exist for the requested path.
    Skips (with a warning log) any individual data point file that cannot be read,
    rather than crashing the entire request.
    """

    # --- Step 1: Build the path to the marker folder ---
    # The archive hierarchy is: archive_root / subject_id / module_id / marker_id /
    # e.g. data/archive/subject_001/vtf_stress_test/vo2max/
    marker_folder = os.path.join(archive_root, subject_id, module_id, marker_id)

    # --- Step 2: Load index.json ---
    # index.json is the time-ordered manifest of all data point files for this marker.
    # We use it for filtering rather than scanning raw filenames, because filenames use
    # hyphens instead of colons (Windows filesystem compatibility) and are harder to
    # parse reliably.
    index_path = os.path.join(marker_folder, "index.json")

    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"No index.json found at {index_path}. "
            f"Check that subject_id='{subject_id}', module_id='{module_id}', "
            f"and marker_id='{marker_id}' are correct and that data exists in the archive."
        )

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    # index["entries"] is a list of dicts, each with "timestamp" and "file" keys:
    # [{ "timestamp": "2026-01-05T08:00:00Z", "file": "2026-01-05T08-00-00Z.json" }, ...]
    entries = index["entries"]

    # --- Step 3: Filter entries to the requested time range ---
    # We parse each entry's timestamp string into a datetime object for comparison.
    # All timestamps in the archive are UTC, so we attach timezone.utc to make them
    # timezone-aware. This is required to compare them against from_time and to_time,
    # which must also be timezone-aware (the caller is responsible for this).
    filtered_entries = []
    for entry in entries:
        # datetime.fromisoformat() parses "2026-01-05T08:00:00Z" — but Python < 3.11
        # does not support the trailing 'Z' directly, so we replace it with '+00:00'.
        entry_time = datetime.fromisoformat(
            entry["timestamp"].replace("Z", "+00:00")
        )

        # Include entries whose timestamp falls within [from_time, to_time] inclusive.
        if from_time <= entry_time <= to_time:
            filtered_entries.append(entry)

    # --- Step 4: Read each matching data point file ---
    datapoints = []
    for entry in filtered_entries:
        file_path = os.path.join(marker_folder, entry["file"])

        try:
            with open(file_path, encoding="utf-8") as f:
                datapoint = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Log a warning and skip this file rather than crashing the whole request.
            # This makes the system resilient to a single corrupt or missing file.
            logger.warning(
                "Skipping data point file '%s': %s", file_path, e
            )
            continue

        # Add a parsed_timestamp field (Python datetime) alongside the original
        # string timestamp. The trajectory computer needs this for arithmetic
        # (computing hours elapsed since the earliest point).
        datapoint["parsed_timestamp"] = datetime.fromisoformat(
            datapoint["timestamp"].replace("Z", "+00:00")
        )

        datapoints.append(datapoint)

    # --- Step 5: Sort chronologically and return ---
    # The index.json should already be in order, but we sort explicitly here to
    # guarantee correct ordering even if the index was manually edited out of sequence.
    datapoints.sort(key=lambda dp: dp["parsed_timestamp"])

    return datapoints
