# this code is to scrape requests and responses from the linkedin signin page
# we want to analyze what kind of requests and responses are sent so we can see
# what headers and cookies we need to scrape and save for later use

import os
import random
import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# type imports
from playwright.sync_api import Page, BrowserContext, Browser, Request, Response

# load environment variables
load_dotenv()

# get linkedin credentials
EMAIL = os.getenv("TEST_EMAIL")
PASS = os.getenv("TEST_PASS")

# create pandas dataframes to store requests and responses
request_df = pd.DataFrame(columns=["url", "method", "headers", "body"])
response_df = pd.DataFrame(columns=["url", "status", "headers", "body"])

# list of user agents to pick from
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
]

# set up playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        geolocation={"latitude": random.uniform(-90, 90), "longitude": random.uniform(-180, 180)}
    )
    page = context.new_page()

    page.goto("https://www.linkedin.com/login")

    # fill in the email and password fields
    page.fill("#username", EMAIL)
    page.fill("#password", PASS)
    print("Filled in email and password")

    # before we click the sign in button, we need to intercept the requests
    # and responses
    def intercept_request(request: Request) -> None:
        global request_df

        # we only want requests pertaining to the Voyager API
        if "voyager" not in request.url.lower():
            return

        # we also only want Voyager requests with a valid csrf token
        if "csrf-token" not in request.headers:
            return

        print(f"Intercepted request to: {request.url} of type: {request.method}")

        # get the request url, method, headers, and body
        url = request.url
        method = request.method
        headers = request.all_headers()
        body = request.post_data

        # add the request to the dataframe
        data_to_add = pd.DataFrame(
            [[url, method, headers, body]], columns=["url", "method", "headers", "body"]
        )
        request_df = pd.concat([request_df, data_to_add])

    def intercept_response(response: Response) -> None:
        global response_df

        # we only want responses pertaining to the Voyager API
        if "voyager" not in response.url.lower():
            return

        print(f"Intercepted response to: {response.url} with status: {response.status}")

        # get the response url, status, headers, and body
        url = response.url
        status = response.status
        headers = response.all_headers()
        body = response.body

        # add the response to the dataframe
        data_to_add = pd.DataFrame(
            [[url, status, headers, body]], columns=["url", "status", "headers", "body"]
        )
        response_df = pd.concat([response_df, data_to_add])

    # intercept requests and responses
    page.on("request", lambda request: intercept_request(request))
    page.on("response", lambda response: intercept_response(response))

    # click the sign in button
    page.click("button[type=submit]")

    # wait for the page to load
    page.wait_for_load_state("networkidle")

    # wait a good chunk of time for the requests to finish
    print("Waiting for requests to finish...")
    page.wait_for_timeout(1000 * 60)

    # close the browser
    browser.close()
    print("Closed browser")

# save the dataframes to csv files
# if the file already exists, increment the file name
request_file_name = "experiments/results/request_data.csv"
response_file_name = "experiments/results/response_data.csv"
i = 1
while os.path.exists(request_file_name):
    request_file_name = f"experiments/results/request_data_{i}.csv"
    i += 1
i = 1
while os.path.exists(response_file_name):
    response_file_name = f"experiments/results/response_data_{i}.csv"
    i += 1
request_df.to_csv(request_file_name, index=False)
response_df.to_csv(response_file_name, index=False)


# print the dataframes
print(request_df)
print(response_df)
