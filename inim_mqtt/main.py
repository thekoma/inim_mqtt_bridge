#!/usr/bin/env python3
"""This stupid webapp catches the latest podcast from ilpost.it ."""
import myconst
import os
import time
import logging
import log
import redis
logger = log.setup_custom_logger('root')
logger.debug('main message')

import orjson, json
import asyncio
import aiohttp
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from typing import Union
from fastapi import FastAPI, status, Response, Request
from fastapi.responses import PlainTextResponse, ORJSONResponse, HTMLResponse
import inim

# Load Environment Variables from file

load_dotenv()
time.tzset()

# # Set the user agnet to something credible.

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     asyncio.create_task(main())
#     yield
# # Initialize FastAPI
# app = FastAPI(lifespan=lifespan)

# @app.get("/ping", response_class=PlainTextResponse, status_code=200)
# async def ping():
#     """Pong"""
#     return "pong"

def main():
    """Main function"""
    # Create a inimCentral object.

    r = redis.Redis(
        host=myconst.REDIS_HOST, port=myconst.REDIS_PORT, db=myconst.REDIS_DB, socket_timeout=1
    )

    myinim = inim.central(
        redis=r,
        username=myconst.EMAIL,
        password=myconst.PASSWORD,
        pin=myconst.PIN,
        client_id=myconst.CLIENTID,
        client_name=myconst.CLIENTNAME,
        device_id=myconst.DEVICEID,
    )

    # Make a request to the remote API.
    # response = remote_api.register_client()

    # While loop with sleep for 30 seconds
    while True:
        # Check the token validity.
        response=myinim.GetDeviceAreas()
        print(response)
        # time.sleep(myconst.MAXPOLL_TIME)
        time.sleep(5)

if __name__ == "__main__":
    main()