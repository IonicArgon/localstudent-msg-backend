import queue
import threading
import uuid
import datetime
from enum import Enum
from typing import TypedDict, Unpack
from requests.models import Response

# importing the classes
# ? filterer goes here
# ? scraper goes here
# ? url generator goes here
# ? connector goes here
# ? database access goes here


# typing
class JobTypes(Enum):
    CONNECT = 1
    SCRAPE = 2
    FILTER = 3
    DATABASE = 4
    SETTING = 5

class DatabaseOperationTypes(Enum):
    ADD_CONTACTED_LEADS = 1
    ADD_SETUPS = 2
    GET_CONTACTED_LEADS = 3
    GET_SETUPS = 4
    REMOVE_CONTACTED_LEADS = 5
    REMOVE_SETUPS = 6
    UPDATE_CONTACTED_LEADS = 7
    UPDATE_SETUPS = 8

class Job(TypedDict):
    job_type: JobTypes
    job_data: dict


class JobSchedulerInit(TypedDict):
    job_scheduling_interval: int  # how many days between each job
    connection_retries: int  # how many times to retry connecting to a profile
    # ? i cant think of other things to add here, but breaking this out
    # ? into a dict allows me to add more things later without breaking
    # ? the code


# main class
class JobScheduler:
    def __init__(self, **kwargs: Unpack[JobSchedulerInit]):
        # any kwargs
        self.m_job_scheduling_interval = kwargs["job_scheduling_interval"]
        self.m_connection_retries = kwargs["connection_retries"]

        # date stuff
        self.m_last_scheduling_date = None
        self.m_current_date = None

        # job queue
        self.m_job_queue = queue.Queue()
        self.m_current_job = None

        # threading related
        self.m_job_thread = None
        self.m_job_thread_running = False
        self.m_job_scheduling_thread = None
        self.m_job_scheduling_thread_running = False

        # database access
        self.m_database_access = None  # todo: add this

        # filterer
        self.m_filterer = None  # todo: add this

        # scraper
        self.m_scraper = None  # todo: add this

        # url generator
        self.m_url_generator = None  # todo: add this

        # connector
        self.m_connector = None  # todo: add this

        # set up stuff will be below here once i have everything set up
        # todo: add this

    def __del__(self):
        self._stop_job_thread()
        self._stop_job_scheduling_thread()

    # private
    def _start_job_thread(self):
        if self.m_job_thread_running:
            return

        self.m_job_thread_running = True
        self.m_job_thread = threading.Thread(target=self._process_jobs)
        self.m_job_thread.start()

    def _stop_job_thread(self):
        if not self.m_job_thread_running:
            return

        self.m_job_thread_running = False
        self.m_job_thread.join()

    def _start_job_scheduling_thread(self):
        if self.m_job_scheduling_thread_running:
            return

        self.m_job_scheduling_thread_running = True
        self.m_job_scheduling_thread = threading.Thread(
            target=self._schedule_scrape_jobs
        )
        self.m_job_scheduling_thread.start()

    def _stop_job_scheduling_thread(self):
        if not self.m_job_scheduling_thread_running:
            return

        self.m_job_scheduling_thread_running = False
        self.m_job_scheduling_thread.join()

    def _process_jobs(self):
        while self.m_job_thread_running:
            # get the job
            self.m_current_job = self.m_job_queue.get()

            # process the job
            if self.m_current_job["job_type"] == JobTypes.CONNECT:
                leads: list[dict] = self.m_current_job["job_data"]["leads"]
                message: str = self.m_current_job["job_data"]["passthrough"]["message"]
                recruiter: dict = self.m_current_job["job_data"]["passthrough"][
                    "recruiter"
                ]

                successful_leads = []
                unsuccessful_leads = []

                for lead in leads:
                    # check if this lead is over the retry limit
                    if lead["retry_count"] >= self.m_connection_retries:
                        print(
                            f"{JobScheduler.__name__}: WARNING - dropping lead {lead['profile_id']} because it has exceeded the retry limit of {self.m_connection_retries}"
                        )
                        continue

                    lead_first_name: str = lead["first_name"]
                    recruiter_first_name: str = recruiter["first_name"]
                    formatted_message: str = message.format(
                        lead_first_name=lead_first_name,
                        recruiter_first_name=recruiter_first_name,
                    )

                    profile = self.m_connector.get_profile(lead["profile_id"])
                    profile_urn = self.m_connector.get_profile_urn(profile)
                    response: Response = self.m_connector.connect_to_profile(
                        profile_urn, message=formatted_message
                    )

                    if response.status_code == 200:
                        successful_leads.append(lead)
                    else:
                        lead["retry_count"] += 1
                        unsuccessful_leads.append(lead)

                # successful leads will be added to the database
                self.m_job_queue.put(
                    {
                        "job_type": JobTypes.DATABASE,
                        "job_data": {
                            "leads": successful_leads,
                            "operation_type": DatabaseOperationTypes.ADD_CONTACTED_LEADS,
                        },
                    }
                )

                # unsuccessful leads still within the retry limit will be added back to the queue
                self.m_job_queue.put(
                    {
                        "job_type": JobTypes.CONNECT,
                        "job_data": {
                            "leads": unsuccessful_leads,
                            "passthrough": {
                                "message": message,
                                "recruiter": recruiter,
                            },
                        },
                    }
                )

            elif self.m_current_job["job_type"] == JobTypes.SCRAPE:
                keywords = self.m_current_job["job_data"]["keywords"]
                per_page = self.m_current_job["job_data"]["per_page"]
                max_candidates = self.m_current_job["job_data"]["max_candidates"]

                # todo: we need to get the url from the url generator
                # todo: and we currently don't have a way to do that

                #! note that this doesn't work because it doesn't exist
                url = self.m_url_generator.generate_url(keywords)

                # scrape the leads
                self.m_scraper.scrape(url, can_count=per_page, can_end=max_candidates)

                # now set up a new job to filter the leads
                job_data = {
                    "leads": None,
                    "passthrough": {
                        "message": self.m_current_job["job_data"]["passthrough"][
                            "message"
                        ],
                        "recruiter": self.m_current_job["job_data"]["passthrough"][
                            "recruiter"
                        ],
                    },
                }
                job_data["leads"] = self.m_scraper.get_leads()

                self.m_job_queue.put(
                    {
                        "job_type": JobTypes.FILTER,
                        "job_data": job_data,
                    }
                )

            elif self.m_current_job["job_type"] == JobTypes.FILTER:
                leads = self.m_current_job["job_data"]["leads"]

                # first, filter the leads to get rid of any unused info
                self.m_filterer.filter_leads(leads)

                # now, get the database so we can ignore any leads we
                # already contacted
                #! note that this doesn't work because it doesn't exist
                contacted_leads = self.m_database_access.get_contacted_leads()
                self.m_filterer.ignore_contacted_leads(contacted_leads)

                # now we pass the leads to the connector through a job
                job_data = {
                    "leads": None,
                    "passthrough": {
                        "message": self.m_current_job["job_data"]["passthrough"][
                            "message"
                        ],
                        "recruiter": self.m_current_job["job_data"]["passthrough"][
                            "recruiter"
                        ],
                    },
                }
                lead_data = []
                for lead in leads:
                    lead_data.append(
                        {
                            "retry_count": 0,
                            **lead,
                        }
                    )
                job_data["leads"] = lead_data

                self.m_job_queue.put(
                    {
                        "job_type": JobTypes.CONNECT,
                        "job_data": job_data,
                    }
                )

            elif self.m_current_job["job_type"] == JobTypes.DATABASE:
                # todo: add this
                pass

            elif self.m_current_job["job_type"] == JobTypes.SETTING:
                # todo: add this
                pass

            # mark the job as done
            self.m_current_job = None
            self.m_job_queue.task_done()

    ## this specifically is to look through our list of setups from the
    ## Cloud Firestore database and schedule scraping jobs for each one
    ## ? scraping jobs because that's what initiates the whole process
    def _schedule_scrape_jobs(self):
        while self.m_job_scheduling_thread_running:
            # get the current date
            self.m_current_date = datetime.datetime.now()

            # check if we need to schedule jobs
            if (
                self.m_last_scheduling_date is None
                or (self.m_current_date - self.m_last_scheduling_date).days
                >= self.m_job_scheduling_interval
            ):
                # get the setups from the database
                setups = self.m_database_access.get_setups()

                # schedule the jobs
                for setup in setups:
                    job_data = {
                        "keywords": setup["keywords"],
                        "per_page": setup["per_page"],
                        "max_candidates": setup["max_candidates"],
                        "passthrough": {
                            "message": setup["message"],
                            "recruiter": setup["recruiter"],
                        },
                    }

                    self.m_job_queue.put(
                        {"job_type": JobTypes.SCRAPE, "job_data": job_data}
                    )

                # update the last scheduling date
                self.m_last_scheduling_date = self.m_current_date
