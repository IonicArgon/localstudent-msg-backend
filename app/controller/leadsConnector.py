# imports up here
import pandas as pd
from base import Base

# temporary imports for testing and stuff
import os
import json


# exceptions
class LinkedInMemberObjDoesNotExist(Exception):
    pass


class LinkedInMemberObjMalformed(Exception):
    pass


class LeadsConnector(Base):
    def __init__(self, headers: str = None, cookies: str = None):
        super().__init__(headers=headers, cookies=cookies)
        self.m_filtered_leads = []
        self.m_previous_connections = []

    def get_filtered_leads(self) -> list:
        return self.m_filtered_leads
    
    def get_previous_connections(self) -> list:
        return self.m_previous_connections

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

    def get_profile(self, profile_id: str) -> dict:
        params = {
            "q": "memberIdentity",
            "memberIdentity": profile_id,
            "decorationId": "com.linkedin.voyager.dash.deco.identity.profile.WebTopCardCore-16",
        }

        self.m_session.headers.update({"User-Agent": self.get_user_agent()})

        response = self.m_session.get(
            "https://www.linkedin.com/voyager/api/identity/dash/profiles",
            params=params,
            timeout=10,
        )

        if response.status_code != 200:
            return None
        
        return response.json()
    
    def connect_to_profile(self, profile_urn, message: str = ""):
        params = {
            "action": "verifyQuotaAndCreate",
            "decorationId": "com.linkedin.voyager.dash.deco.relationships.InvitationCreationResult-3"
        }

        payload = {
            "inviteeProfileUrn": profile_urn,
            "customMessage": message
        }

        self.m_session.headers.update({"User-Agent": self.get_user_agent()})

        print(f"attempting to connect to {profile_urn} with message {message}")

        response = self.m_session.post(
            "https://www.linkedin.com/voyager/api/voyagerRelationshipsDashMemberRelationships",
            params=params,
            json=payload,
            timeout=10
        )

        if response.status_code != 200 or response.status_code != 500:
            print(f"Failed to connect to {profile_urn} with status code {response.status_code}\n")
            print("The following is debug info:")
            print(json.dumps(response.json(), indent=4))
            print("Response headers:")
            print(json.dumps(dict(response.headers), indent=4))
            print("Response cookies:")
            print(json.dumps(dict(response.cookies), indent=4))
            return None
        
        return response.json()

## quick testing
if __name__ == "__main__":
    connector = LeadsConnector(
        headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
        cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
    )

    leads = None
    with open(os.path.join(os.getcwd(), "test/leads.json"), "r", encoding="utf-8") as f:
        leads = json.load(f)

    print("filtering lead data")
    connector.filter_leads(leads)

    print("writing to file")
    with open("test/filtered_leads.json", "w", encoding="utf-8") as f:
        json.dump(connector.get_filtered_leads(), f, indent=4)

    # try to get the profile
    print("getting profile")
    profile = connector.get_profile(connector.get_filtered_leads()[0]["profile_id"])
    profile_urn = profile.get("elements")[0].get("memberRelationship").get("memberRelationshipUnion").get("noConnection").get("invitationUnion").get("noInvitation").get("inviter")
    print(profile_urn)

    # lets try to connect
    message = None
    with open("test/testMessage.txt", "r", encoding="utf-8") as f:
        message = f.read()

    print("connecting to profile")
    response = connector.connect_to_profile(profile_urn, message=message)
    print(response)