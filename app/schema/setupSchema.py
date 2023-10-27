class MalformedSetupSchema(Exception):
    pass


class SetupSchema:
    def __init__(
        self,
        recruiter_id: str,
        recruiter_identity_id: str,
        recruiter_name: str,
        base_message: str,
        search_keywords: list[str],
        frequency: int,
    ):
        self.m_recruiter_id = recruiter_id
        self.m_recruiter_identity_id = recruiter_identity_id
        self.m_recruiter_name = recruiter_name
        self.m_base_message = base_message
        self.m_search_keywords = search_keywords
        self.m_frequency = frequency

        # if any of the required fields are missing, raise an exception
        members = vars(self)
        for member in members:
            if member.startswith("m_") and not members[member]:
                raise MalformedSetupSchema(f"Missing required header {member[2:]}")

    def get_recruiter_id(self):
        return self.m_recruiter_id
    
    def get_recruiter_identity_id(self):
        return self.m_recruiter_identity_id
    
    def get_recruiter_name(self):
        return self.m_recruiter_name
    
    def get_base_message(self):
        return self.m_base_message
    
    def get_keywords(self):
        return self.m_search_keywords
    
    def get_frequency(self):
        return self.m_frequency