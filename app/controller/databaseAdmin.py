import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# schema import
from app.schema.identitySchema import IdentitySchema
from app.schema.leadSchema import LeadSchema
from app.schema.setupSchema import SetupSchema


class DatabaseAdmin:
    def __init__(self, service_account_json: str):
        cred = credentials.Certificate(service_account_json)
        firebase_admin.initialize_app(cred)
        self.m_db = firestore.client()

    def add_contacted_leads(self, leads: list[LeadSchema]):
        for lead in leads:
            self.m_db.collection("contacted_leads").document(lead.get_profile_id()).set(
                {
                    "first_name": lead.get_first_name(),
                    "last_name": lead.get_last_name(),
                    "profile_id": lead.get_profile_id(),
                }
            )

    def add_setup(self, setup: SetupSchema):
        self.m_db.collection("setups").document(setup.get_recruiter_id()).set(
            {
                "base_message": setup.get_base_message(),
                "frequency": setup.get_frequency(),
                "identity_id": setup.get_recruiter_identity_id(),
                "first_name": setup.get_recruiter_first_name(),
                "last_name": setup.get_recruiter_last_name(),
                "search_keywords": setup.get_keywords(),
            }
        )

    def get_contacted_leads(self) -> list[LeadSchema]:
        leads = []
        for lead in self.m_db.collection("contacted_leads").stream():
            leads.append(
                LeadSchema(
                    lead.get("first_name"),
                    lead.get("last_name"),
                    lead.get("profile_id"),
                )
            )
        return leads

    def get_setup(self, setup_id: str) -> SetupSchema:
        setup = self.m_db.collection("setups").document(setup_id).get()
        return SetupSchema(
            recruiter_id=setup_id,
            recruiter_identity_id=setup.get("identity_id"),
            recruiter_first_name=setup.get("first_name"),
            recruiter_last_name=setup.get("last_name"),
            base_message=setup.get("base_message"),
            search_keywords=setup.get("search_keywords"),
            frequency=setup.get("frequency"),
        )
    
    def get_setups(self) -> list[SetupSchema]:
        setups = []
        for setup in self.m_db.collection("setups").stream():
            setups.append(
                SetupSchema(
                    recruiter_id=setup.id,
                    recruiter_identity_id=setup.get("identity_id"),
                    recruiter_first_name=setup.get("first_name"),
                    recruiter_last_name=setup.get("last_name"),
                    base_message=setup.get("base_message"),
                    search_keywords=setup.get("search_keywords"),
                    frequency=setup.get("frequency"),
                )
            )
        return setups
    
    def remove_contacted_leads(self, leads: list[LeadSchema]):
        for lead in leads:
            self.m_db.collection("contacted_leads").document(lead.get_profile_id()).delete()

    def remove_setup(self, setup_id: str):
        self.m_db.collection("setups").document(setup_id).delete()

    def update_contacted_leads(self, leads: list[LeadSchema]):
        for lead in leads:
            self.m_db.collection("contacted_leads").document(lead.get_profile_id()).update(
                {
                    "first_name": lead.get_first_name(),
                    "last_name": lead.get_last_name(),
                    "profile_id": lead.get_profile_id(),
                }
            )

    def update_setup(self, setup: SetupSchema):
        self.m_db.collection("setups").document(setup.get_recruiter_id()).update(
            {
                "base_message": setup.get_base_message(),
                "frequency": setup.get_frequency(),
                "identity_id": setup.get_recruiter_identity_id(),
                "first_name": setup.get_recruiter_first_name(),
                "last_name": setup.get_recruiter_last_name(),
                "search_keywords": setup.get_keywords(),
            }
        )
