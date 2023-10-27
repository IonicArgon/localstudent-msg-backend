class MalformedLeadSchema(Exception):
    pass


class LeadSchema:
    def __init__(self, first_name: str, last_name: str, profile_id: str):
        self.m_first_name = first_name
        self.m_last_name = last_name
        self.m_profile_id = profile_id

        # if any of the required fields are missing, raise an exception
        members = vars(self)
        for member in members:
            if member.startswith("m_") and not members[member]:
                raise MalformedLeadSchema(f"Missing required header {member[2:]}")

    def get_first_name(self):
        return self.m_first_name

    def get_last_name(self):
        return self.m_last_name

    def get_profile_id(self):
        return self.m_profile_id
