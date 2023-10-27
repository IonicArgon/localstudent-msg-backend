class MalformedSetupSchema(Exception):
    pass


class SetupSchema:
    def __init__(
        self,
        recruiter_id: str,
        recruiter_identity_id: str,
        recruiter_first_name: str,
        recruiter_last_name: str,
        base_message: str,
        search_keywords: dict[str, str],
        frequency: int,
        candidates_per_page: int,
        max_candidates: int,
    ):
        self.m_recruiter_id = recruiter_id
        self.m_recruiter_identity_id = recruiter_identity_id
        self.m_recruiter_first_name = recruiter_first_name
        self.m_recruiter_last_name = recruiter_last_name
        self.m_base_message = base_message
        self.m_search_keywords = search_keywords
        self.m_frequency = frequency
        self.m_candidates_per_page = candidates_per_page
        self.m_max_candidates = max_candidates

        # if any of the required fields are missing, raise an exception
        members = vars(self)
        for member in members:
            if member.startswith("m_") and not members[member]:
                raise MalformedSetupSchema(f"Missing required header {member[2:]}")

    def get_recruiter_id(self):
        return self.m_recruiter_id
    
    def get_recruiter_identity_id(self):
        return self.m_recruiter_identity_id
    
    def get_recruiter_first_name(self):
        return self.m_recruiter_name
    
    def get_recruiter_last_name(self):
        return self.m_recruiter_last_name
    
    def get_recruiter_name(self):
        return self.m_recruiter_first_name + " " + self.m_recruiter_last_name
    
    def get_base_message(self):
        return self.m_base_message
    
    def get_keywords(self):
        return self.m_search_keywords
    
    def get_frequency(self):
        return self.m_frequency
    
    def get_candidates_per_page(self):
        return self.m_candidates_per_page
    
    def get_max_candidates(self):
        return self.m_max_candidates