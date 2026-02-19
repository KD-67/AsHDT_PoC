import json
import os
import logging
from datetime import datetime, timezone


logger = logging.getLogger(__name__)

def read_timeseries(
    archive_root: str,
    subject_id: str,
    module_id: str,
    marker_id: str,
    from_time: datetime,
    to_time: datetime,
) -> list[dict]:

    marker_folder = os.path.join(archive_root, subject_id, module_id, marker_id)

    index_path = os.path.join(marker_folder, "index.json")

    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"No index.json found at {index_path}. "
            f"Check that subject_id='{subject_id}', module_id='{module_id}', "
            f"and marker_id='{marker_id}' are correct and that data exists in the archive."
        )

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    entries = index["entries"]

    filtered_entries = []
    for entry in entries:
        entry_time = datetime.fromisoformat(
            entry["timestamp"].replace("Z", "+00:00")
        )
        if from_time <= entry_time <= to_time:
            filtered_entries.append(entry)

    datapoints = []
    for entry in filtered_entries:
        file_path = os.path.join(marker_folder, entry["file"])

        try:
            with open(file_path, encoding="utf-8") as f:
                datapoint = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(
                "Skipping data point file '%s': %s", file_path, e
            )
            continue

        datapoint["parsed_timestamp"] = datetime.fromisoformat(
            datapoint["timestamp"].replace("Z", "+00:00")
        )

        datapoints.append(datapoint)

    datapoints.sort(key=lambda dp: dp["parsed_timestamp"])

    return datapoints
