#? i'm creating this because in case this code changes later, it's better if i
#? just break it out

# no imports currently

# exceptions
class LinkedInMemberObjDoesNotExist(Exception):
    pass

class LinkedInMemberObjMalformed(Exception):
    pass

class LinkedInProfileObjMalformed(Exception):
    pass

class LeadsFilterer():
    def __init__(self):
        self.m_filtered_leads = []

    def filter_leads(self, unfiltered_leads: list):
        for lead in unfiltered_leads:
            linkedin_member_obj = lead.get(
                "linkedInMemberProfileUrnResolutionResult", None
            )

            # we need to check if the profile is out of network and if so, skip it
            hidden_reason = linkedin_member_obj.get("fullProfileNotVisibleReason", None)
            reference_urn = linkedin_member_obj.get("referenceUrn", None)
            if hidden_reason is not None:
                print(f"Skipping {reference_urn} because of reason {hidden_reason}")
                continue

            #! if the obj doesn't exist smth is really wrong with the scraping
            if linkedin_member_obj is None:
                raise LinkedInMemberObjDoesNotExist(
                    "LinkedIn member object does not exist! Check the scraping!"
                )

            first_name = linkedin_member_obj.get("unobfuscatedFirstName", None)
            last_name = linkedin_member_obj.get("unobfuscatedLastName", None)

            if first_name is None:
                first_name = linkedin_member_obj.get("firstName", None)
            if last_name is None:
                last_name = linkedin_member_obj.get("lastName", None)

            profile_url = linkedin_member_obj.get("publicProfileUrl", None)

            #! if there is no first name, last name, or profile url, linkedin did a big stinky
            if first_name is None or last_name is None or profile_url is None:
                raise LinkedInMemberObjMalformed(
                    "LinkedIn member object is malformed! Maybe LinkedIn changed their API?"
                )
            
            profile_id = profile_url.split("/in/")[1]

            self.m_filtered_leads.append(
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "profile_id": profile_id,
                }
            )

            # check for duplicates
            self.m_filtered_leads = [
                dict(t) for t in {tuple(d.items()) for d in self.m_filtered_leads}
            ]

    def get_filtered_leads(self) -> list:
        return self.m_filtered_leads
    
    def reset(self):
        self.m_filtered_leads = []