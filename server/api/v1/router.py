from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from fastapi import APIRouter, UploadFile, Query, File, Form
from fastapi.responses import JSONResponse
from server.api.v1.model import ChatModel, ForgetModel, LearnModel
from share.types import EventMetadata, Response, List, Optional

# from share.errors import ErrorType

from server.service import upload_controller
from utils import common, validate
from share import var

v1_router = APIRouter(prefix="/v1", tags=["v1"])


@v1_router.get("/id")
async def get_trace_id():
    """
    Get a trace_id to add to the request body of any API that can be tracked.

    Returns:
        JSONResponse: A JSON response containing the trace_id and its age (in seconds)
    """
    ulid = common.generate_ulid()

    var.UNUSED_ID_CACHE[ulid] = True

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=Response(
            err_code=0,
            err_msg="Success",
            data={"trace_id": ulid, "age": var.CONFIG.cache.unused_id.ttl},
        ).to_dict(),
    )


@v1_router.get("/event/{event_id}")
async def get_event(event_id: str):
    """
    Get an event by its event_id(a trace_id that has been assigned to a event).

    Args:
        event_id (str): The id of the event to retrieve.

    Returns:
        JSONResponse: A JSON response containing the event data if the event is found,
            or a 404 error if the event does not exist.
    """
    if event_id in var.CACHE:
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content=Response(
                err_code=0,
                err_msg="Found event",
                data=var.CACHE[event_id],
            ).to_dict(),
        )
    else:
        # check db
        event = var.EVENT_MANAGER.get_event("upload", event_id)

        if event:
            var.CACHE[event_id] = event
            return JSONResponse(
                status_code=HTTPStatus.OK,
                content=Response(
                    err_code=0,
                    err_msg="Found event",
                    data=event,
                ).to_dict(),
            )
        else:
            return JSONResponse(
                status_code=HTTPStatus.NOT_FOUND,
                content=Response(
                    err_code=HTTPStatus.NOT_FOUND,
                    err_msg="Not found",
                    data=None,
                ).to_dict(),
            )


@v1_router.post("/upload/")
async def upload(
    attachments: List[UploadFile] = File(...),
    collection_name: str = Form(default="default"),
    trace_id: str = Form(default=None),
):
    """
    Upload a file to the server.

    Args:
        attachments (List[UploadFile]): A list of files to upload.
        collection_name (str, optional): The name of the collection to upload to. Defaults to "default".
        trace_id (str, optional): The trace id of the upload event. If not provided, a new one will be generated.

    Returns:
        JSONResponse: A JSON response containing the event data of the upload event.

    Note:
        The collection name must conform to the following rules:

        (1) contains 3-63 characters
        (2) starts and ends with an alphanumeric character
        (3) otherwise contains only alphanumeric characters, underscores or hyphens (-)
        (4) contains no two consecutive periods (..)
        (5) is not a valid IPv4 address
    """
    if trace_id and trace_id not in var.UNUSED_ID_CACHE:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=Response(
                err_code=HTTPStatus.BAD_REQUEST,
                err_msg="Invalid or expired trace_id",
                data=None,
            ).to_dict(),
        )

    try:
        validate.collection_name_rule(collection_name)
    except ValueError as e:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=Response(
                err_code=HTTPStatus.BAD_REQUEST,
                err_msg=str(e),
                data=None,
            ).to_dict(),
        )

    if any([attachment.size == 0 for attachment in attachments]):
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=Response(
                err_code=HTTPStatus.BAD_REQUEST,
                err_msg="No file uploaded",
                data=None,
            ).to_dict(),
        )

    if trace_id:
        var.UNUSED_ID_CACHE.pop(trace_id)

    trace_id = trace_id if trace_id else common.generate_ulid()

    event_data: EventMetadata = EventMetadata(
        event_id=trace_id,
        type="upload",
        status="pending",
        detail={"progress": 0, "included": []},
    )

    # set cache
    var.CACHE[event_data.event_id] = event_data.to_dict()

    # set db
    var.EVENT_MANAGER.new_event_type(event_data.type)
    var.EVENT_MANAGER.add_event(event_data.type, event_data)

    var.FILE_MANAGER.new_collection(collection_name)

    await upload_controller.v1_upload(event_data, attachments, collection_name)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=Response(
            err_code=0,
            err_msg=f"The file(s) are uploaded successfully, id: {trace_id}",
            data=event_data.to_dict(),
        ).to_dict(),
    )


@v1_router.get("/file/{collection_name}")
async def get_file_list(collection_name: str):
    """
    Retrieve the list of files including their metadata in a specified collection.

    Args:
        collection_name (str): The name of the collection whose file list is to be retrieved.

    Returns:
        JSONResponse: A JSON response containing the file list if the collection is found,
                      or a 404 error if the collection does not exist.
    """

    result, err_msg = var.FILE_MANAGER.get_file_list(collection_name)

    if not result:
        return JSONResponse(
            status_code=HTTPStatus.NOT_FOUND,
            content=Response(
                err_code=HTTPStatus.NOT_FOUND,
                err_msg=err_msg,
                data=result,
            ).to_dict(),
        )
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=Response(
            err_code=0,
            err_msg=err_msg,
            data=result,
        ).to_dict(),
    )


@v1_router.get("/file/{collection_name}/{file_id}")
async def get_file(collection_name: str, file_id: str):
    """
    Retrieve a file's metadata from a specified collection.

    Args:
        collection_name (str): The name of the collection whose file metadata is to be retrieved.
        file_id (str): The id of the file whose metadata is to be retrieved.

    Returns:
        JSONResponse: A JSON response containing the file metadata if the collection and file are found,
                      or a 404 error if the collection or file does not exist.
    """
    result, err_msg = var.FILE_MANAGER.get_file_metadata(collection_name, file_id)

    if not result:
        return JSONResponse(
            status_code=HTTPStatus.NOT_FOUND,
            content=Response(
                err_code=HTTPStatus.NOT_FOUND,
                err_msg=err_msg,
                data=result,
            ).to_dict(),
        )
    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=Response(
            err_code=0,
            err_msg=err_msg,
            data=result,
        ).to_dict(),
    )


@v1_router.post("/chat")
async def chat(payload: ChatModel):
    """
    Chat with the model using a specified collection.

    Args:
        collection_name (str): The name of the collection to use for the chat.
        query (str): The user's query.

    Returns:
        JSONResponse: A JSON response containing the model's response if the collection is found,
                      or a 404 error if the collection does not exist.
    """
    if payload.collection_name not in var.RAG_SYSTEM.vector_stores:
        return JSONResponse(
            status_code=HTTPStatus.NOT_FOUND,
            content=Response(
                err_code=HTTPStatus.NOT_FOUND,
                err_msg=f"I didn't learn anything about the collection `{payload.collection_name}`",
                data=None,
            ).to_dict(),
        )

    result, err_msg = var.RAG_SYSTEM.query(payload.collection_name, payload.query)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=Response(
            err_code=0,
            err_msg=err_msg,
            data=result,
        ).to_dict(),
    )


@v1_router.post("/learn")
async def learn(payload: LearnModel):
    """
    Learn a new collection or relearn an existing collection.

    Args:
        collection_name (str): The name of the collection to learn.
        re (bool): Whether to relearn the collection if it already exists.
        tag (str): The tag of the collection.
        author (str): The author of the collection.

    Returns:
        JSONResponse: A JSON response containing the collection info if the collection is learned successfully,
                      or a 400 error if the collection already exists and `re=False`,
                      or a 404 error if the collection does not exist and `re=True`,
                      or a 400 error if the collection is not learned successfully.
    """
    if not payload.re and payload.collection_name in var.RAG_SYSTEM.vector_stores:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=Response(
                err_code=HTTPStatus.BAD_REQUEST,
                err_msg=f"Collection `{payload.collection_name}` already exists\nYou must set `re=True` to relearn this collection",
                data=None,
            ).to_dict(),
        )

    file_list, err_msg = var.FILE_MANAGER.get_file_list(
        payload.collection_name, show_simple=True
    )

    if not file_list:
        # should not happen
        return JSONResponse(
            status_code=HTTPStatus.NOT_FOUND,
            content=Response(
                err_code=HTTPStatus.NOT_FOUND,
                err_msg=err_msg,
                data=file_list,
            ).to_dict(),
        )

    info, err_msg = var.RAG_SYSTEM.create_collection(
        payload.collection_name,
        {
            "tag": payload.tag,
            "author": payload.author,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "included": common.unmarshall_json(file_list),
        },
        f"./upload/{payload.collection_name}",
    )

    if not info:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=Response(
                err_code=HTTPStatus.BAD_REQUEST,
                err_msg=err_msg,
                data=None,
            ).to_dict(),
        )

    info["metadata"]["included"] = common.unmarshall_json(info["metadata"]["included"])

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content=Response(
            err_code=0,
            err_msg=err_msg,
            data=info,
        ).to_dict(),
    )


@v1_router.delete("/forget")
async def forget(payload: ForgetModel):
    """
    Delete the specified collection from the vector store.

    Args:
        payload (ForgetModel): An object containing the name of the collection to be forgotten.

    Returns:
        JSONResponse: A JSON response indicating the success or failure of the operation.
                      Returns a 404 error if the collection does not exist, or a 500 error
                      if there was an internal server error during deletion.
    """

    if payload.collection_name not in var.RAG_SYSTEM.vector_stores:
        return JSONResponse(
            status_code=HTTPStatus.NOT_FOUND,
            content=Response(
                err_code=HTTPStatus.NOT_FOUND,
                err_msg=f"I didn't learned anything about the collection `{payload.collection_name}`",
                data=None,
            ).to_dict(),
        )

    result, err_mag = var.RAG_SYSTEM.delete_collection(payload.collection_name)
    status_code = HTTPStatus.OK if result else HTTPStatus.INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content=Response(
            err_code=0,
            err_msg=err_mag,
            data=None,
        ).to_dict(),
    )
