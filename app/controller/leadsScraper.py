from app.controller.base import Base

# temporary imports until i figure out how im going to store identities
import os
import json

class LeadsScraper(Base):
    def __init__(self, headers: str = None, cookies: str = None):
        super().__init__(headers=headers, cookies=cookies)
        self.m_leads = []
        self.m_previous_start_param = "start=0"
        self.m_previous_lead_count = 0
        self.m_lead_change_counter = 0

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
if __name__ == "__main__":
    fetcher = LeadsScraper(
        headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
        cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
    )

    url = None
    with open("test/links/testViper.txt", "r") as f:
        url = f.read()

    print("about to scrape")
    fetcher.scrape(url, can_count=25, can_end=2000)

    print("scraping complete, writing to file")
    with open("test/leads.json", "w") as f:
        json.dump(fetcher.get_leads(), f, indent=4)
