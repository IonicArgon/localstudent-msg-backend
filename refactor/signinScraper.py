# imports
import random
import threading
import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import stealth_sync
from app.controller.base import Base

# type imports
from playwright.sync_api import Page, BrowserContext, Browser, Request, Response
from threading import Event

# temporary imports for testing and stuff
import os
import sys
import json
from dotenv import load_dotenv


# exceptions that i can think of
class LinkedInSignInFailed(Exception):
    pass


class VoyagerRequestNotFound(Exception):
    pass


class NoEventProvided(Exception):
    pass


# class
class SigninScraper(Base):
    def __init__(
        self,
        headers: str = None,
        cookies: str = None,
        event: Event = None,
        dashboard_time: int = 15,  # this is in seconds
    ):
        super().__init__(headers=headers, cookies=cookies)
        self.m_request_df = pd.DataFrame(columns=["url", "method", "headers", "body"])
        self.m_verification_code = None
        self.m_event = event
        self.m_waiting_for_2fa = False
        self.m_status = None

        # playwright stuff
        self.m_browser = None
        self.m_context = None
        self.m_page = None
        self.m_dashboard_time = 1000 * dashboard_time

        # threading stuff
        self.m_thread = None

        if self.m_event is None:
            raise NoEventProvided("No event was provided to the SigninScraper class.")

    def __del__(self):
        if self.m_browser is not None:
            self.m_browser.close()

    # private

    def _get_random_geo_location(self) -> dict:
        return {
            "latitude": random.uniform(-90, 90),
            "longitude": random.uniform(-180, 180),
        }

    def _intercept_request(self, request: Request) -> None:
        if "voyager" not in request.url.lower() or "csrf-token" not in request.headers:
            return

        print(f"Intercepted request to: {request.url} of type: {request.method}")

        # add the request to the dataframe
        self.m_request_df = pd.concat(
            [
                self.m_request_df,
                pd.DataFrame(
                    data=[
                        [
                            request.url,
                            request.method,
                            request.all_headers(),
                            request.post_data,
                        ]
                    ],
                    columns=["url", "method", "headers", "body"],
                ),
            ]
        )

    def _scrape(self, email: str, password: str) -> None:
        with sync_playwright() as p:
            self.m_browser: Browser = p.chromium.launch()
            self.m_context: BrowserContext = self.m_browser.new_context(
                user_agent=self.get_user_agent(),
                geolocation=self._get_random_geo_location(),
            )
            self.m_page: Page = self.m_context.new_page()
            stealth_sync(self.m_page)

            # setup request interception
            self.m_page.on("request", self._intercept_request)

            self.m_page.goto("https://www.linkedin.com/login")
            self.m_page.fill("#username", email)
            self.m_page.fill("#password", password)
            self.m_page.click("button[type=submit]")

            while True:
                if "checkpoint" in self.m_page.url and self.m_page.get_by_text("Let's do a quick security check"):
                    self.m_status = -1
                    return
                elif "checkpoint" in self.m_page.url and self.m_page.get_by_text("Enter"):
                    print(f"{SigninScraper.__name__}: Waiting for 2FA code...")
                    self.m_waiting_for_2fa = True
                    self.m_event.wait()

                    self.m_page.fill("[id*='verification_pin']", self.m_verification_code)
                    self.m_page.click("button[type=submit]")

                    if "checkpoint" in self.m_page.url:
                        print(f"{SigninScraper.__name__}: 2FA code was incorrect.")
                        self.m_event.clear()
                        self.m_verification_code = None
                        continue
                    else:
                        self.m_waiting_for_2fa = False
                        break

            self.m_page.wait_for_load_state("networkidle")
            self.m_page.wait_for_timeout(self.m_dashboard_time)
            self.m_browser.close()

        # check if the df is empty
        if self.m_request_df.empty:
            raise VoyagerRequestNotFound("No voyager requests were found.")
        
        self.m_status = 0

    # public

    def get_request_df(self) -> pd.DataFrame:
        return self.m_request_df

    def get_verification_code(self) -> str:
        return self.m_verification_code

    def is_waiting_for_2fa(self) -> bool:
        return self.m_waiting_for_2fa

    def set_verification_code(self, code: str) -> None:
        self.m_verification_code = code

    def reset(self):
        self.m_request_df = pd.DataFrame(columns=["url", "method", "headers", "body"])
        self.m_response_df = pd.DataFrame(columns=["url", "status", "headers", "body"])
        self.m_verification_code = None

    def scrape(self, email: str, password: str) -> None:
        self.m_thread = threading.Thread(target=self._scrape, args=(email, password))
        self.m_thread.start()

    def join(self) -> int:
        self.m_thread.join()
        return self.m_status


## testing
# if __name__ == "__main__":
#     load_dotenv()

#     # get the email and password from the environment
#     EMAIL = os.getenv("TEST_EMAIL")
#     PASS = os.getenv("TEST_PASS")

#     # 2fa events
#     event = Event()

#     # create a scraper
#     scraper = SigninScraper(
#         headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
#         cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
#         event=event,
#         dashboard_time=20,
#     )

#     # set up thread stuff
#     def code_input_thread(event: Event) -> None:
#         verification_code = input("Enter the 2FA code: ")
#         scraper.set_verification_code(verification_code)
#         event.set()

#     code_input_thread = threading.Thread(target=code_input_thread, args=(event,))
#     code_input_thread.start()
#     scraper.scrape(EMAIL, PASS)
#     print("test to see if this method is blocking")
#     code_input_thread.join()

#     request_file_name = "test/request_data.csv"
#     i = 1
#     while os.path.exists(request_file_name):
#         request_file_name = f"test/request_data_{i}.csv"
#         i += 1
#     scraper.get_request_df().to_csv(request_file_name, index=False)
