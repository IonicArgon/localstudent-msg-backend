import queue
import threading
import time
import uuid
from flask import Blueprint, request, jsonify
from app.controller.leadsConnector import LeadsConnector

# temporary imports to get it working
import os
import json

# set up connector
#! this is not permanent, this is just for testing
#todo: remove this and make it so our identity changes based on recruiter
connector = LeadsConnector(
    headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
    cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
)

# setup request queue
request_queue = queue.Queue()
current_request = None

# queue for processed requests
processed_requests: dict = {}

# set up the thread to process requests
def process_requests():
    global current_request

    while True:
        # get request
        current_request = request_queue.get()
        print(f"Processing request {current_request[0]}")

        # process the request
        leads: list = current_request[2]["leads"]
        base_message: str = current_request[2]["message"]
        recruiter_name: str = current_request[2]["recruiter_name"]
        
        # connect to each lead
        for lead in leads:
            lead_id = lead["profile_id"]
            lead_name = lead["name"]
            lead_message = base_message.replace("{name}", lead_name).replace("{recruiter_name}", recruiter_name)
            
            profile = connector.get_profile(lead_id)
            lead_urn = connector.get_profile_urn(profile)
            response = connector.connect_to_profile(lead_urn, message=lead_message)

            # add the response to the processed requests
            if current_request[0] not in processed_requests:
                processed_requests[current_request[0]] = {}
                processed_requests[current_request[0]]["request_time"] = current_request[1]
                processed_requests[current_request[0]]["responses"] = []

            processed_requests[current_request[0]]["responses"].append(
                {
                    "lead_id": lead_id,
                    "lead_name": lead_name,
                    "response": response.json(),
                }
            )

        # mark the task as done
        request_queue.task_done()

        # reset
        current_request = None

# start the thread
thread = threading.Thread(target=process_requests)
thread.daemon = True
thread.start()

# create the blueprint
connect_route_bp = Blueprint("connect_route", __name__)

# create the route
@connect_route_bp.route("/connect", methods=["POST"])
def connect_to_profiles():
    # generate uuid
    request_id = str(uuid.uuid4())

    # get time of request
    request_time = time.time()

    # get the request data
    data = request.get_json()

    # check for valid request data
    if "leads" not in data or type(data["leads"]) != list:
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
    
    # add the request to the queue
    request_queue.put((request_id, request_time, data))

    # return the request id
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

# create the route to get processed requests
@connect_route_bp.route("/connect/<request_id>", methods=["GET"])
def get_connect_status(request_id: str):
    # check if the request has been processed
    for i, key in enumerate(processed_requests.keys()):
        if key == request_id:
            # get the responses stored there
            processed = processed_requests[key]

            # remove that entry from the dictionary
            del processed_requests[key]

            # return the responses
            return (
                jsonify(
                    {
                        "request_id": request_id,
                        "request_time": processed["request_time"],
                        "responses": processed["responses"],
                        "message": "Request has been processed",
                    }
                ),
                200,
            )
        
    # check if the request is currently being processed
    if current_request is not None and current_request[0] == request_id:
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
    
    # check if the request is still being processed
    for i, (id, time, _) in enumerate(request_queue.queue):
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