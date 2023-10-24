import queue
import threading
import time
import uuid
from flask import Blueprint, request, jsonify
from app.controller.leadsScraper import LeadsScraper
from app.controller.leadsFilterer import LeadsFilterer

# temporary imports to get this working
import os

# set up the scraper first
scraper = LeadsScraper(
    headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
    cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
)

# set up the filterer
filterer = LeadsFilterer()

# set up request queue functionality
request_queue = queue.Queue()
current_request = None

# queue for processed requests
processed_requests: dict = {}

# set up the thread to process requests
def process_requests():
    global current_request

    while True:
        # get the request from the queue
        current_request = request_queue.get()
        print(f"Processing request {current_request[0]}")

        # process the request
        # ? for now, our url is fixed
        url = None
        with open("test/links/testibio.txt", "r") as f:
            url = f.read()

        # scrape the url
        request_can_count = current_request[2]["can_count"]
        request_can_end = current_request[2]["can_end"]

        # while loop until scrape is ready to be used again
        while True:
            status = scraper.scrape(
                url, can_count=request_can_count, can_end=request_can_end
            )

            if status == 0:
                break
            elif status == -1:
                print("Scrape is not ready to be used again")
                time.sleep(1)

        # filter the leads
        filterer.filter_leads(scraper.get_leads())

        # add the processed data to the processed requests queue
        if current_request[0] not in processed_requests:
            processed_requests[current_request[0]] = filterer.get_filtered_leads()

        # reset the scraper
        scraper.reset()
        current_request = None

        # mark the task as done
        request_queue.task_done()


# start the thread
process_thread = threading.Thread(target=process_requests)
process_thread.daemon = True
process_thread.start()

# set up the blueprint
leads_route_bp = Blueprint("leads_route", __name__)


# set up the route
@leads_route_bp.route("/leads", methods=["POST"])
def add_leads():
    # generate uuid
    request_id = str(uuid.uuid4())

    # get time of request
    request_time = time.time()

    # get the request data
    request_data = request.get_json()

    # check if the request data is valid
    if ("can_count" not in request_data or "can_end" not in request_data) or (
        type(request_data["can_count"]) != int or type(request_data["can_end"]) != int
    ):
        return (
            jsonify(
                {
                    "request_id": request_id,
                    "request_time": request_time,
                    "message": "Invalid request data",
                }
            ),
            400,
        )

    # add the request to the queue
    request_queue.put((request_id, request_time, request_data))

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


# set up routes for individual requests
@leads_route_bp.route("/leads/<request_id>", methods=["GET"])
def get_lead_status(request_id: str):
    # check if the request has been processed
    for i, key in enumerate(processed_requests.keys()):
        if key == request_id:
            # get the data
            data = processed_requests[key]

            # remove the entry from the dictionary
            del processed_requests[key]

            # return the data
            return (
                jsonify(
                    {
                        "request_id": request_id,
                        "data": data,
                    }
                ),
                200,
            )
        
    # check if our request is currently being processed
    if current_request != None and current_request[0] == request_id:
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

    return (
        jsonify(
            {
                "request_id": request_id,
                "message": "Request not found",
            }
        ),
        404,
    )
