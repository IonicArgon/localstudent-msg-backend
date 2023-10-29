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

from app.controller.databaseAdmin import DatabaseAdmin
from app.schema.identitySchema import IdentitySchema
from app.schema.leadSchema import LeadSchema
from app.schema.setupSchema import SetupSchema


# typing
class JobTypes(Enum):
    CONNECT = 1
    SCRAPE = 2
    FILTER = 3
    DATABASE = 4
    SETTING = 5


class DatabaseOperationTypes(Enum):
    ADD_CONTACTED_LEADS = 1
    ADD_SETUP = 2
    GET_CONTACTED_LEADS = 3
    GET_SETUP = 4
    REMOVE_CONTACTED_LEADS = 5
    REMOVE_SETUP = 6
    UPDATE_CONTACTED_LEADS = 7
    UPDATE_SETUP = 8


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

        # processed jobs
        self.m_processed_jobs = {}

        # threading related
        self.m_job_thread = None
        self.m_job_thread_running = False
        self.m_job_scheduling_thread = None
        self.m_job_scheduling_thread_running = False

        # database access
        self.m_database_access = DatabaseAdmin(
            ".environment/linkedin-automation-401619-5d531a7232e5.json"
        )

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

    def _job_connect(self):
        leads: list[dict] = self.m_current_job["job_data"]["leads"]
        message: str = self.m_current_job["job_data"]["passthrough"]["message"]
        recruiter: dict = self.m_current_job["job_data"]["passthrough"]["recruiter"]

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
                lead=lead_first_name,
                recruiter=recruiter_first_name,
            )

            profile = self.m_connector.get_profile(lead["profile_id"])
            profile_urn = self.m_connector.get_profile_urn(profile)
            response: Response = self.m_connector.connect_to_profile(
                profile_urn, message=formatted_message
            )

            if response.status_code == 200 or response.status_code == 500:
                successful_leads.append(lead)
            else:
                lead["retry_count"] += 1
                unsuccessful_leads.append(lead)

        # successful leads will be added to the database
        successful_leads_schema = []
        for lead in successful_leads:
            successful_leads_schema.append(
                LeadSchema(
                    first_name=lead["first_name"],
                    last_name=lead["last_name"],
                    profile_id=lead["profile_id"],
                )
            )

        self.m_job_queue.put(
            {
                "job_id": self.m_current_job["job_id"],
                "job_type": JobTypes.DATABASE,
                "job_data": {
                    "leads": successful_leads_schema,
                    "operation_type": DatabaseOperationTypes.ADD_CONTACTED_LEADS,
                },
            }
        )

        # unsuccessful leads still within the retry limit will be added back to the queue
        if unsuccessful_leads:
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

        # add to the processed jobs

    def _job_scrape(self):
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
                "message": self.m_current_job["job_data"]["passthrough"]["message"],
                "recruiter": self.m_current_job["job_data"]["passthrough"]["recruiter"],
                "identity_id": self.m_current_job["job_data"]["passthrough"]["identity_id"],
            },
        }
        job_data["leads"] = self.m_scraper.get_leads()

        self.m_job_queue.put(
            {
                "job_id": self.m_current_job["job_id"],
                "job_type": JobTypes.FILTER,
                "job_data": job_data,
            }
        )

    def _job_filter(self):
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
                "message": self.m_current_job["job_data"]["passthrough"]["message"],
                "recruiter": self.m_current_job["job_data"]["passthrough"]["recruiter"],
                "identity_id": self.m_current_job["job_data"]["passthrough"]["identity_id"],
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
                "job_id": self.m_current_job["job_id"],
                "job_type": JobTypes.CONNECT,
                "job_data": job_data,
            }
        )

    def _job_database(self):
        operation_type = self.m_current_job["job_data"]["operation_type"]

        if operation_type == DatabaseOperationTypes.ADD_CONTACTED_LEADS:
            leads = self.m_current_job["job_data"]["leads"]
            self.m_database_access.add_contacted_leads(leads)
        elif operation_type == DatabaseOperationTypes.ADD_SETUP:
            setup = self.m_current_job["job_data"]["setup"]
            self.m_database_access.add_setup(setup)
        elif operation_type == DatabaseOperationTypes.GET_CONTACTED_LEADS:
            leads = self.m_database_access.get_contacted_leads()
            return leads
        elif operation_type == DatabaseOperationTypes.GET_SETUP:
            setup_id = self.m_current_job["job_data"]["setup_id"]
            setup = self.m_database_access.get_setup(setup_id)
            return setup
        elif operation_type == DatabaseOperationTypes.REMOVE_CONTACTED_LEADS:
            leads = self.m_current_job["job_data"]["leads"]
            self.m_database_access.remove_contacted_leads(leads)
        elif operation_type == DatabaseOperationTypes.REMOVE_SETUP:
            setup_id = self.m_current_job["job_data"]["setup_id"]
            self.m_database_access.remove_setup(setup_id)
        elif operation_type == DatabaseOperationTypes.UPDATE_CONTACTED_LEADS:
            leads = self.m_current_job["job_data"]["leads"]
            self.m_database_access.update_contacted_leads(leads)
        elif operation_type == DatabaseOperationTypes.UPDATE_SETUP:
            setup = self.m_current_job["job_data"]["setup"]
            self.m_database_access.update_setup(setup)

    def _job_setting(self):
        job_schedule_interval = self.m_current_job["job_data"]["settings"][
            "job_scheduling_interval"
        ]
        connection_retries = self.m_current_job["job_data"]["settings"][
            "connection_retries"
        ]

        # update
        self.m_job_scheduling_interval = job_schedule_interval
        self.m_connection_retries = connection_retries

    def _process_jobs(self):
        while self.m_job_thread_running:
            # get the job
            self.m_current_job = self.m_job_queue.get()

            # process the job
            if self.m_current_job["job_type"] == JobTypes.CONNECT:
                self._job_connect()
            elif self.m_current_job["job_type"] == JobTypes.SCRAPE:
                self._job_scrape()
            elif self.m_current_job["job_type"] == JobTypes.FILTER:
                self.job_filter()
            elif self.m_current_job["job_type"] == JobTypes.DATABASE:
                # todo: add this
                pass

            elif self.m_current_job["job_type"] == JobTypes.SETTING:
                self._job_setting()

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
                        "keywords": setup.get_keywords(),
                        "per_page": setup.get_candidates_per_page(),
                        "max_candidates": setup.get_max_candidates(),
                        "passthrough": {
                            "message": setup.get_base_message(),
                            "recruiter": {
                                "first_name": setup.get_recruiter_first_name(),
                                "last_name": setup.get_recruiter_last_name(),
                            },
                            "identity_id": setup.get_recruiter_identity_id(),
                        },
                    }

                    self.m_job_queue.put(
                        {
                            "job_id": f"auto_schedule_{setup.get_recruiter_id()}_{uuid.uuid4()}",
                            "job_type": JobTypes.SCRAPE,
                            "job_data": job_data,
                        }
                    )

                # update the last scheduling date
                self.m_last_scheduling_date = self.m_current_date
