# imports up here
import pandas as pd
from base import Base

# type import
from requests.models import Response

# temporary imports for testing and stuff
import os
import sys
import json


# exceptions
class LinkedInMemberObjDoesNotExist(Exception):
    pass

class LinkedInMemberObjMalformed(Exception):
    pass

class LinkedInProfileObjMalformed(Exception):
    pass

class LeadsConnector(Base):
    def __init__(self, headers: str = None, cookies: str = None):
        super().__init__(headers=headers, cookies=cookies)

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
    
    def get_profile_urn(self, json_data: dict) -> str:
        elements_first = json_data.get("elements", None)[0]

        if elements_first is None:
            raise LinkedInProfileObjMalformed(
                "LinkedIn profile object is malformed! Maybe LinkedIn changed their API?"
            )
        
        # look for a value starting with "urn:li:fsd_profile:" within the json
        for value in elements_first.values():
            if isinstance(value, str) and value.startswith("urn:li:fsd_profile:"):
                return value
        
        # if we get here, then we didn't find a value
        raise LinkedInProfileObjMalformed(
            "LinkedIn profile object is malformed! Maybe LinkedIn changed their API?"
        )
    
    def connect_to_profile(self, profile_urn, message: str = "") -> Response:
        params = {
            "action": "verifyQuotaAndCreateV2",
            "decorationId": "com.linkedin.voyager.dash.deco.relationships.InvitationCreationResultWithInvitee-2"
        }

        payload = {
            "invitee": {
                "inviteeUnion": {
                    "memberProfile": profile_urn
                }
            },
            "customMessage": message,
        }

        self.m_session.headers.update({"User-Agent": self.get_user_agent()})

        print(f"attempting to connect to {profile_urn} with message {message}")

        response = self.m_session.post(
            "https://www.linkedin.com/voyager/api/voyagerRelationshipsDashMemberRelationships",
            params=params,
            json=payload,
            timeout=10
        )

        #! if it fails with a 400 with the code "CANT_RESEND_YET" then we'll need to wait like 3 weeks
        #todo: add a check for this
        
        return response

## quick testing
# if __name__ == "__main__":
#     connector = LeadsConnector(
#         headers=os.path.join(os.getcwd(), "test/identities/mike/headers.json"),
#         cookies=os.path.join(os.getcwd(), "test/identities/mike/cookies.json"),
#     )

#     leads = None
#     with open(os.path.join(os.getcwd(), "test/leads.json"), "r", encoding="utf-8") as f:
#         leads = json.load(f)

#     print("filtering lead data")
#     connector.filter_leads(leads)

#     print("writing to file")
#     with open("test/filtered_leads.json", "w", encoding="utf-8") as f:
#         json.dump(connector.get_filtered_leads(), f, indent=4)

#     # try to get the profile
#     print("getting profile")
#     profile = connector.get_profile(connector.get_filtered_leads()[0]["profile_id"])
#     profile_urn = connector.get_profile_urn(profile)
#     response_connection = connector.connect_to_profile(profile_urn, message="Hello, I'm Mike Johnson!")

#     # dump whole response (data, headers, cookies, etc.) to file
#     print("writing response to file")
#     with open("test/response.json", "w", encoding="utf-8") as f:
#         json.dump(response_connection.json(), f, indent=4)
#         json.dump(dict(response_connection.headers), f, indent=4)
#         json.dump(dict(response_connection.cookies), f, indent=4)
