import os

from fastapi import UploadFile
from share import var
from share.types import List, EventMetadata, FileMetadata
from utils.common import generate_ulid, generate_hash
from time import time


async def v1_upload(
    event_data: EventMetadata,
    files: List[UploadFile],
    collection_name: str = "default",
) -> None:
    total_size = sum(file.size for file in files)
    start_update_time = time()
    current_size = 0
    progress = 0
    included = []

    for file in files:
        file_type = file.content_type.split("/")[-1]
        file_id = generate_ulid()
        dir_path = os.path.join(f"{var.CONFIG.upload.dir}", collection_name, file_type)
        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, file_id + f".{file_type}")

        with open(file_path, "wb") as buffer:
            chunk_size = 10240

            while chunk := await file.read(chunk_size):
                if not chunk:
                    break

                buffer.write(chunk)
                current_size += len(chunk)

                progress = int((current_size / total_size) * 100)

                if time() - start_update_time < 2:
                    continue

                start_update_time = time()
                _update_event(event_data, "running", progress, included)

        _update_file_record(
            collection_name,
            {
                "id": file_id,
                "path": file_path,
                "name": file.filename,
                "size": file.size,
                "upload_id": event_data.event_id,
            },
        )

        included.append({"file_id": file_id, "file_name": file.filename})
        _update_event(event_data, "running", progress, included)

    _update_event(event_data, "success", 100, included)


def _update_event(
    event_data: EventMetadata, status: str, progress: int, included: list
) -> None:
    var.CACHE[event_data.event_id]["status"] = status
    var.CACHE[event_data.event_id]["detail"]["progress"] = progress
    var.CACHE[event_data.event_id]["detail"]["included"] = included

    metadata: EventMetadata = EventMetadata(
        event_id=event_data.event_id,
        type=event_data.type,
        status=status,
        detail={"progress": progress, "included": included},
    )

    var.EVENT_MANAGER.update_event(
        event_type=event_data.type,
        metadata=metadata,
    )


def _update_file_record(collection_name: str, file_data: dict) -> None:
    with open(file_data["path"], "rb") as f:
        content = f.read()
    content_hash = generate_hash(content)

    var.FILE_MANAGER.add_file(
        collection_name,
        FileMetadata(
            file_data["id"],
            content_hash,
            file_data["path"],
            file_data["name"],
            file_data["size"],
            file_data["upload_id"],
        ),
    )
