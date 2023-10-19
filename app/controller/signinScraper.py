# imports
from playwright.sync_api import sync_playwright
from base import Base

# temporary imports for testing and stuff
import os
import sys
import json
from dotenv import load_dotenv


# exceptions that i can think of
class LinkedIn2FARequired(Exception):
    pass

class LinkedInSignInFailed(Exception):
    pass

class VoyagerSearchDashSearchHomeRequestNotFound(Exception):
    pass

# class
class SigninScraper(Base):
    def __init__(self, headers: str = None, cookies: str = None):
        super().__init__(headers=headers, cookies=cookies)
        self.m_browser = None
        self.m_context = None
        self.m_page = None

        self.m_cookies = None
        self.m_headers = None

        self.m_2fa = None

        self.m_request_events = []

    def __del__(self):
        if self.m_browser is not None:
            self.m_browser.close()

    def get_cookies(self) -> str:
        return self.m_cookies
    
    def get_headers(self) -> str:
        return self.m_headers
    
    def set_2fa(self, code: str):
        self.m_2fa = code
    
    # currently i think i'll just return an int for the status code
    # we're gonna have to do this async because of 2FA
    def scrape_requests(self, email: str, password: str) -> None:
        with sync_playwright() as p:
            self.m_browser = p.chromium.launch()
            self.m_context = self.m_browser.new_context(
                user_agent=self.get_user_agent()
            )
            self.m_page = self.m_context.new_page()
            print("Created page")

            # go to the linkedin login page
            self.m_page.goto("https://www.linkedin.com/login")

            # fill in the email and password fields
            self.m_page.fill("#username", email)
            self.m_page.fill("#password", password)
            print("Filled in email and password")

            # click the sign in button
            self.m_page.click("button[type=submit]")
            self.m_page.wait_for_load_state("networkidle")

            # check if we're on the 2FA page
            if "https://www.linkedin.com/checkpoint/" in self.m_page.url:
                # we're on the 2FA page, wait for a code to be entered
                print("Waiting for 2FA code...")
                while self.m_2fa is None:
                    pass

                # fill in the 2FA code
                self.m_page.fill("#input__email_verification_pin", self.m_2fa)
                self.m_page.click("button[type=submit]")
                print("Filled in 2FA code")

                # check if we're on the 2FA page again
                if "https://www.linkedin.com/checkpoint/" in self.m_page.url:
                    # we're still on the 2FA page, so the code was wrong
                    raise LinkedIn2FARequired("2FA code was incorrect!")
                
            # check if we're not on the home page and if so, then we failed to sign in
            if not "https://www.linkedin.com/feed/" in self.m_page.url:
                raise LinkedInSignInFailed("Failed to sign in!")
            
            # first we need to subscribe to all request events
            self.m_page.on("request", lambda request: self.m_request_events.append(request))
            print("Subscribed to request events")

            # now we need to search something so we can find VoyagerSearchDashHome
            self.m_page.fill("input[aria-label='Search']", "test")
            self.m_page.press("input[aria-label='Search']", "Enter")
            print("Searched for test")

            # we'll find the cookies and headers in another function
            self.m_page.close()
            self.m_context.close()
            self.m_browser.close()
            print("Closed page")
    
    def process_requests(self) -> None:
        # look for the VoyagerSearchDashHome request
        voyagerRequest = None
        for request in self.m_request_events:
            if "voyagerSearchDash" in str(request.url):
                voyagerRequest = request
                break

        # if we didn't find the request, then we failed to scrape the requests
        if voyagerRequest is None:
            raise VoyagerSearchDashSearchHomeRequestNotFound("Failed to find VoyagerSearchDash request!")
        
        # get our cookies and headers from the request
        self.m_cookies = voyagerRequest.headers.get("cookie", None)
        self.m_headers = voyagerRequest.headers.get("headers", None)

        # if we didn't get the cookies or headers, then we failed to scrape the requests
        if self.m_cookies is None or self.m_headers is None:
            raise VoyagerSearchDashSearchHomeRequestNotFound("Failed to find VoyagerSearchDash request!")
        

## quick testing
if __name__ == "__main__":
    load_dotenv()

    email = os.getenv("TEST_EMAIL")
    password = os.getenv("TEST_PASS")

    scraper = SigninScraper(
        headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
        cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
    )

    # # we need to run this in a thread because we need to wait for the 2FA code to be entered
    # # we'll join the thread after we pass the 2FA code
    # thread = threading.Thread(target=scraper.scrape_requests, args=(email, password))
    # thread.start()

    # # wait for the 2FA code to be entered
    # twofa = input("Enter 2FA code: ")
    # scraper.set_2fa(twofa)

    scraper.set_2fa("123456")
    scraper.scrape_requests(email, password)

    # process the requests
    scraper.process_requests()

    # print the cookies and headers
    print(scraper.get_cookies())
    print(scraper.get_headers())
