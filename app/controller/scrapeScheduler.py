import queue
import threading
import uuid
import datetime
from typing import TypedDict, Unpack, Optional
from requests.models import Response

from app.controller.leadsScraper import LeadsScraper
from app.controller.leadsFilterer import LeadsFilterer

# todo: add "from app.controller.urlGenerator import UrlGenerator"
# todo: when the url generator is done
from app.controller.databaseAdmin import DatabaseAdmin

# schemas for data passed between classes
from app.schema.identitySchema import IdentitySchema
from app.schema.leadSchema import LeadSchema
from app.schema.setupSchema import SetupSchema

# typing
from app.types.jobTypes import JobTypes, Job, JobReturn
from app.types.databaseOperationsTypes import DatabaseOperationTypes


class ScrapeSchedulerKwargs(TypedDict):
    scheduling_interval: int
    identity: IdentitySchema
    db_admin: DatabaseAdmin
    # ? don't know what else to put here


class ScrapeScheduler:
    def __init__(self, **kwargs: Unpack[ScrapeSchedulerKwargs]):
        self.m_scheduling_interval: int = kwargs["scheduling_interval"]
        self.m_identity: IdentitySchema = kwargs["identity"]
        self.m_db_admin: DatabaseAdmin = kwargs["db_admin"]

        # date stuff
        self.m_last_scheduled_date: Optional[datetime.datetime] = None
        self.m_current_date: Optional[datetime.datetime] = None

        # job queue, processed, threading
        self.m_job_queue: queue.Queue = queue.Queue()
        self.m_current_job: Optional[Job] = None
        self.m_processed_jobs: list[JobReturn] = []
        self.m_processed_jobs_lock = threading.Lock()
        self.m_thread: threading.Thread = None
        self.m_thread_running: bool = False

        self.m_filterer = LeadsFilterer()
        self.m_scraper = LeadsScraper(
            headers=self.m_identity.json(), cookies=self.m_identity.json_cookie()
        )
        # todo: add "self.m_url_generator = UrlGenerator()"
        # todo: when the url generator is done

        self._start_thread()

    def __del__(self):
        self._stop_thread()

    # private
    def _start_thread(self) -> None:
        if self.m_thread_running:
            return

        self.m_thread_running = True
        self.m_thread = threading.Thread(target=self._thread_loop)
        self.m_thread.start()

    def _stop_thread(self) -> None:
        if not self.m_thread_running:
            return

        self.m_thread_running = False
        self.m_thread.join()

    def _thread_loop(self) -> None:
        while self.m_thread_running:
            self.m_current_job = self.m_job_queue.get()

            keywords: dict[str, str] = self.m_current_job["job_data"]["keywords"]
            per_page: int = self.m_current_job["job_data"]["per_page"]
            max_candidates: int = self.m_current_job["job_data"]["max_candidates"]

            # todo: we still need the url generator
            #! we can't test this until the url generator is done
            url = self.m_url_generator.generate_url(keywords=keywords)

            # scrape the leads
            self.m_scraper.scrape(url=url, can_end=max_candidates, can_count=per_page)

            # filter the leads
            self.m_filterer.filter_leads(self.m_scraper.get_leads())

            # remove previously contacted leads
            contacted_leads = self.m_db_admin.get_contacted_leads()
            self.m_filterer.ignore_contacted_leads(contacted_leads)

            # add filtered leads to processed jobs
            lead_data = []
            for lead in self.m_filterer.get_filtered_leads():
                lead_data.append(
                    {
                        "retry_count": 0,
                        "lead": LeadSchema(
                            first_name=lead["first_name"],
                            last_name=lead["last_name"],
                            profile_id=lead["profile_id"],
                        ),
                    }
                )

            with self.m_processed_jobs_lock:
                self.m_processed_jobs.append(
                    JobReturn(
                        job_id=self.m_current_job["job_id"],
                        job_type=self.m_current_job["job_type"],
                        job_return_data=lead_data,
                    )
                )

            # reset the filterer and scraper, mark the job as done
            self.m_filterer.reset()
            self.m_scraper.reset()
            self.m_job_queue.task_done()

    # public
    def schedule(self, job: Job) -> None:
        # check if the job is valid
        if job["job_type"] != JobTypes.SCRAPE:
            return

        # check if the job is already scheduled
        if job["job_id"] in [job["job_id"] for job in self.m_job_queue.queue]:
            return

        # add the job to the queue
        self.m_job_queue.put(job)

        # start the thread if it's not running
        self._start_thread()

    def get_processed_jobs(self) -> list[JobReturn]:
        with self.m_processed_jobs_lock:
            processed_jobs = self.m_processed_jobs
            self.m_processed_jobs = []
            return processed_jobs
