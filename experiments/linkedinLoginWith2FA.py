# this an attempt to login to linkedin with 2FA
# the idea is to have two threads, one main thread and one thread that
# waits for the 2FA code to be entered manually by the user

import os
import random
import threading
import pandas as pd
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# type imports
from playwright.sync_api import Page, BrowserContext, Browser, Request, Response
from threading import Event

# load environment variables
load_dotenv()

# get linkedin credentials
EMAIL = os.getenv("TEST_EMAIL")
PASS  = os.getenv("TEST_PASS")

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

# threading events to signal when the 2FA code has been entered
code_entered = threading.Event()
verification_code = None

# first we create the playwright thread
def playwright_logic(event: Event) -> None:
    global verification_code
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=False)
        context: BrowserContext = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            geolocation={"latitude": random.uniform(-90, 90), "longitude": random.uniform(-180, 180)}
        )
        page: Page = context.new_page()

        # intercept requests and responses
        def intercept_request(request: Request) -> None:
            global request_df

            if "voyager" not in request.url.lower() or "csrf-token" not in request.headers:
                return
            
            print(f"Intercepted request to: {request.url} of type: {request.method}")

            # add the request to the dataframe
            request_df = pd.concat([
                request_df,
                pd.DataFrame(
                    data=[[request.url, request.method, request.all_headers(), request.post_data]],
                    columns=["url", "method", "headers", "body"]
                )
            ])

        def intercept_response(response: Response) -> None:
            global response_df

            if "voyager" not in response.url.lower():
                return
            
            print(f"Intercepted response to: {response.url} of type: {response.status}")

            # add the response to the dataframe
            response_df = pd.concat([
                response_df,
                pd.DataFrame(
                    data=[[response.url, response.status, response.all_headers(), response.body]],
                    columns=["url", "status", "headers", "body"]
                )
            ])

        # set up request and response interception
        page.on("request", intercept_request)
        page.on("response", intercept_response)

        page.goto("https://www.linkedin.com/login")
        page.fill("#username", EMAIL)
        page.fill("#password", PASS)
        page.click("button[type=submit]")
        print("Filled in email and password")

        # check if we need to enter a 2FA code
        if "checkpoint" in page.url:
            # we need to enter a 2FA code
            print("Waiting for 2FA code...")
            event.wait()
            print("2FA code entered")

            # fill in the 2FA code
            page.fill("[id*='verification_pin']", verification_code)
            page.click("button[type=submit]")
            print("Filled in 2FA code")

        # wait for the page to load, then wait a while longer
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000 * 15)

        # close the browser
        browser.close()
        print("Browser closed")

# next we create the thread that waits for the 2FA code to be entered
def code_input_logic(event: Event) -> None:
    global verification_code
    verification_code = input("Please enter the 2FA code: ")
    event.set()

# start the threads
playwright_thread = threading.Thread(target=playwright_logic, args=(code_entered,))
code_input_thread = threading.Thread(target=code_input_logic, args=(code_entered,))
playwright_thread.start()
code_input_thread.start()

# wait for the threads to finish
playwright_thread.join()
code_input_thread.join()

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
