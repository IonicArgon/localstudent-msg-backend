# this code is to scrape requests and responses from the linkedin signin page
# we want to analyze what kind of requests and responses are sent so we can see
# what headers and cookies we need to scrape and save for later use

import os
import io
import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# type imports
from playwright.sync_api import Page, BrowserContext, Browser, Request, Response

# load environment variables
load_dotenv()

# get linkedin credentials
EMAIL = os.getenv("TEST_EMAIL")
PASS  = os.getenv("TEST_PASS")

# create pandas dataframes to store requests and responses
request_df = pd.DataFrame(columns=["url", "method", "headers", "body"])
response_df = pd.DataFrame(columns=["url", "status", "headers", "body"])

# set up playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
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
            [[url, method, headers, body]],
            columns=["url", "method", "headers", "body"]
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
            [[url, status, headers, body]],
            columns=["url", "status", "headers", "body"]
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
    page.wait_for_timeout(10000)

    # close the browser
    browser.close()
    print("Closed browser")

# save the dataframes to csv files
request_df.to_csv("experiments/results/linkedinRequests.csv")
response_df.to_csv("experiments/results/linkedinResponses.csv")

# print the dataframes
print(request_df)
print(response_df)
