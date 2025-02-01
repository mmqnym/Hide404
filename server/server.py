from http import HTTPStatus
from uvicorn import Config as UvicornConfig, Server
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from server.api.v1.router import v1_router
from share.var import CONFIG, APP_LOG
from share.types import Response

app = FastAPI(
    title="Hide404 API",
    description="Hide404 API helps you query any thing you want. You can get your private LLM service here.",
    summary="Hide404 API helps you query any thing you want.",
    version="0.1.0",
    root_path="/api",
    contact={
        "name": "mmqnym",
        "url": "https://mmq.dev",
        "email": "mail@mmq.dev",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle general request validation errors.

    Args:
        request (Request): The incoming request object.
        exc (RequestValidationError): The exception containing details about the validation error.

    Returns:
        JSONResponse: A JSON response with a 400 status code containing the error details.
    """

    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content=Response(
            err_code=0,
            err_msg="Validation error",
            data=exc.errors(),
        ).to_dict(),
    )


""" add middleware here """
app.add_middleware(CORSMiddleware, CONFIG.middleware.cors.to_dict())

""" add router here """
app.include_router(v1_router)

""" add general background tasks here """
# TODO: add auto deletion of expired events


async def serve() -> None:
    """
    Start the server.

    This function is used to start the server. It will set up the server and start it.
    """
    APP_LOG.info("***** Welcome to use Hide404 API *****")
    APP_LOG.info(f"***** Version: {app.version} *****")
    APP_LOG.info(f"***** License: {app.license_info["name"]} *****")
    APP_LOG.info(f"***** Repository: https://github.com/mmqnym/hide404 *****")
    APP_LOG.info("Starting server...")

    uvicorn_config = UvicornConfig(
        app="server.server:app",
        host=CONFIG.server.host,
        port=CONFIG.server.port,
        access_log=True,
        workers=CONFIG.server.workers,
    )
    server = Server(config=uvicorn_config)

    await server.serve()
