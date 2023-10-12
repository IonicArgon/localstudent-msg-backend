import requests
import random as r

# temporary imports until i figure out how im going to store identities
import os
import json


# exceptions
class InvalidCredentials(Exception):
    pass


class LeadsScraper:
    def __init__(self, headers: str = None, cookies: str = None):
        self.m_headers = None
        self.m_cookies = None
        self.m_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        ]
        self.m_session = requests.Session()
        self.m_leads = []
        self.m_previous_start_param = "start=0"
        self.m_previous_lead_count = 0
        self.m_lead_change_counter = 0

        if headers is not None:
            with open(headers, "r", encoding="utf-8") as f:
                self.m_headers = json.load(f)
        else:
            raise InvalidCredentials("No headers provided")

        if cookies is not None:
            with open(cookies, "r", encoding="utf-8") as f:
                self.m_cookies = json.load(f)
        else:
            raise InvalidCredentials("No cookies provided")

        self.m_session.headers.update(self.m_headers)
        self.m_session.cookies.update(self.m_cookies)

    def get_user_agent(self) -> str:
        return r.choice(self.m_user_agents)

    def get_leads(self) -> list:
        return self.m_leads

    def reset(self):
        self.m_leads = []
        self.m_previous_start_param = "start=0"
        self.m_previous_lead_count = 0
        self.m_lead_change_counter = 0

    def scrape(
        self,
        url: str,
        can_start: int = 0,  # which candidate to start scraping from
        can_count: int = 25,  # how many candidates to scrape per page
        can_end: int = 1000,  # which candidate to stop scraping at
    ):
        # do not run if we alread have leads
        if len(self.m_leads) > 0:
            return -1

        for num_candidates in range(can_start, can_end, can_count):
            # get a random user agent
            self.m_session.headers.update({"User-Agent": self.get_user_agent()})

            # update the url with the new start parameter
            url = url.replace(self.m_previous_start_param, f"start={num_candidates}")
            url = url.replace("count=25", f"count={can_count}")

            # make the request
            response = self.m_session.get(url, timeout=10)

            # check if the request was successful
            if response.status_code != 200:
                break

            # parse the response
            data = response.json()

            # check if there are any leads
            if "elements" not in data:
                break

            # append the leads to the list
            self.m_leads.extend(data["elements"])

            # break early if there are no more leads
            if self.m_lead_change_counter < 3:
                if self.m_previous_lead_count == len(self.m_leads):
                    self.m_lead_change_counter += 1
                else:
                    self.m_lead_change_counter = 0
            else:
                break

            self.m_previous_start_param = f"start={num_candidates}"
            self.m_previous_lead_count = len(self.m_leads)

        return 0


## temporary testing
# if __name__ == "__main__":
#     fetcher = recruiterFetch(
#         headers=os.path.join(os.getcwd(), "identities/mike/headers.json"),
#         cookies=os.path.join(os.getcwd(), "identities/mike/cookies.json"),
#     )

#     url = None
#     with open("links/testibio.txt", "r") as f:
#         url = f.read()

#     print("about to scrape")
#     fetcher.scrape(url, can_count=25, can_end=2000)

#     print("scraping complete, writing to file")
#     with open("leads.json", "w") as f:
#         json.dump(fetcher.get_leads(), f, indent=4)
