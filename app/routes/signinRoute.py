import queue
import threading
import time
import uuid
from flask import Blueprint, jsonify, request
from app.controller.signinScraper import SigninScraper

# type imports as well
from threading import Event

# temporary imports to get it working
import os
import json

# shared variables
event_2fa = Event()
request_queue = queue.Queue()
processed_requests: dict = {}
current_request = None

# set up sign in scraper
#! not sure if this is gonna be permanent
signin_scraper = SigninScraper(
    headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
    cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
    event=event_2fa,
)


# we still need a thread to process the requests
def process_requests():
    global current_request

    while True:
        current_request = request_queue.get()

        email: str = current_request[2]["email"]
        password: str = current_request[2]["password"]

        signin_scraper.reset()
        signin_scraper.scrape(email, password)

        # wait a little bit because if we check too early, we might miss the 2fa
        time.sleep(5)

        # check if we need to wait for 2fa
        if signin_scraper.is_waiting_for_2fa():
            current_request[3]["status"] = "2fa_required"
            event_2fa.wait()

        # get the request df
        request_df = signin_scraper.get_request_df()
        request_df = request_df.to_dict(orient="records")

        # add the request to the processed requests
        if current_request[0] not in processed_requests:
            processed_requests[current_request[0]] = {}
            processed_requests[current_request[0]]["request_time"] = current_request[1]
            processed_requests[current_request[0]]["request_df"] = request_df

        request_queue.task_done()
        current_request = None


# start the thread
thread = threading.Thread(target=process_requests)
thread.daemon = True
thread.start()

# create the blueprint
signin_route = Blueprint("signin_route", __name__)

# define the routes
@signin_route.route("/signin", methods=["POST"])
def signin():
    request_id = str(uuid.uuid4())
    request_time = time.time()
    request_data = request.get_json()

    if (
        "credentials" not in request_data
        or type(request_data["credentials"]) is not dict
    ):
        return (
            jsonify(
                {
                    "message": "Invalid request data",
                    "request_id": request_id,
                    "request_time": request_time,
                }
            ),
            400,
        )

    if (
        "email" not in request_data["credentials"]
        or "password" not in request_data["credentials"]
    ):
        return (
            jsonify(
                {
                    "message": "Invalid request data",
                    "request_id": request_id,
                    "request_time": request_time,
                }
            ),
            400,
        )

    request_queue.put(
        (request_id, request_time, request_data, {"status": "processing"})
    )

    return (
        jsonify(
            {
                "request_id": request_id,
                "request_time": request_time,
                "message": "Request received and queued for processing",
            }
        ),
        202,
    )

@signin_route.route("/signin/<request_id>", methods=["GET", "POST"])
def get_signin_status(request_id: str):
    if request.method == "GET":
        # check if the request has been processed
        for i, key in enumerate(process_requests.keys()):
            if key == request_id:
                processed = processed_requests[key]
                del processed_requests[key]

                return (
                    jsonify(
                        {
                            "request_id": request_id,
                            "request_time": processed["request_time"],
                            "request_df": processed["request_df"],
                        }
                    ),
                    200,
                )
            
        # check if the request is still being processed
        if current_request is not None and current_request[0] == request_id:
            # check if a 2fa is required
            if current_request[3]["status"] == "2fa_required":
                return (
                    jsonify(
                        {
                            "request_id": request_id,
                            "request_time": current_request[1],
                            "message": "Request is currently being processed and requires a 2FA code",
                        }
                    ),
                    428,
                )
            
            return (
                jsonify(
                    {
                        "request_id": request_id,
                        "request_time": current_request[1],
                        "message": "Request is currently being processed",
                    }
                ),
                200,
            )
        
        # check if the request is still in the queue
        for i, (id, time, _, _) in enumerate(request_queue.queue):
            if id == request_id:
                return (
                    jsonify(
                        {
                            "request_id": id,
                            "request_time": time,
                            "message": f"Request is number {i+1} in the queue",
                        }
                    ),
                    200,
                )
            
        # if we get here, then the request doesn't exist
        return (
            jsonify(
                {
                    "request_id": request_id,
                    "message": "Request does not exist",
                }
            ),
            404,
        )
    elif request.method == "POST":
        request_data = request.get_json()

        if "code" not in request_data:
            return (
                jsonify(
                    {
                        "message": "Invalid request data",
                        "request_id": request_id,
                        "request_time": current_request[1],
                    }
                ),
                400,
            )
        
        signin_scraper.set_verification_code(request_data["code"])
        event_2fa.set()

        return (
            jsonify(
                {
                    "message": "2FA code received",
                    "request_id": request_id,
                    "request_time": current_request[1],
                }
            ),
            200,
        )
    