class MalformedIdentitySchema(Exception):
    pass

class IdentitySchema:
    def __init__(
        self,
        authority: str,
        accept: str,
        accept_language: str,
        cookie: str,
        csrf_token: str,
        referer: str,
        sec_ch_ua: str,
        sec_ch_ua_mobile: str,
        sec_ch_ua_platform: str,
        sec_fetch_dest: str,
        sec_fetch_mode: str,
        sec_fetch_site: str,
        user_agent: str,
        x_li_lang: str,
        x_li_page_instance: str,
        x_li_pem_metadata: str,
        x_li_track: str,
        x_restli_protocol_version: str,
    ):
        self.m_authority = authority
        self.m_accept = accept
        self.m_accept_language = accept_language
        self.m_cookie = cookie
        self.m_cookie_dict = self._parse_cookie(cookie)
        self.m_csrf_token = csrf_token
        self.m_referer = referer
        self.m_sec_ch_ua = sec_ch_ua
        self.m_sec_ch_ua_mobile = sec_ch_ua_mobile
        self.m_sec_ch_ua_platform = sec_ch_ua_platform
        self.m_sec_fetch_dest = sec_fetch_dest
        self.m_sec_fetch_mode = sec_fetch_mode
        self.m_sec_fetch_site = sec_fetch_site
        self.m_user_agent = user_agent
        self.m_x_li_lang = x_li_lang
        self.m_x_li_page_instance = x_li_page_instance
        self.m_x_li_pem_metadata = x_li_pem_metadata
        self.m_x_li_track = x_li_track
        self.m_x_restli_protocol_version = x_restli_protocol_version

        # if any of the required headers are missing, raise an exception
        members = vars(self)
        for member in members:
            if member.startswith("m_") and not members[member]:
                raise MalformedIdentitySchema(
                    f"Missing required header {member[2:]}"
                )

    def _parse_cookie(self, cookie: str) -> dict:
        # if cookie is empty, return empty dict
        if not cookie:
            return {}

        # split key value pairs, ; is the delimiter
        cookie_pairs = cookie.split(";")
        cookie_dict = {}
        for pair in cookie_pairs:
            # split key and value, = is the delimiter, split by first occurence
            key, value = pair.split("=", 1)
            cookie_dict[key.strip()] = value
        return cookie_dict
    
    def json_cookie(self) -> dict:
        return self.m_cookie_dict
    
    def json(self) -> dict:
        return {
            "authority": self.m_authority,
            "accept": self.m_accept,
            "accept-language": self.m_accept_language,
            "cookie": self.m_cookie,
            "csrf-token": self.m_csrf_token,
            "referer": self.m_referer,
            "sec-ch-ua": self.m_sec_ch_ua,
            "sec-ch-ua-mobile": self.m_sec_ch_ua_mobile,
            "sec-ch-ua-platform": self.m_sec_ch_ua_platform,
            "sec-fetch-dest": self.m_sec_fetch_dest,
            "sec-fetch-mode": self.m_sec_fetch_mode,
            "sec-fetch-site": self.m_sec_fetch_site,
            "user-agent": self.m_user_agent,
            "x-li-lang": self.m_x_li_lang,
            "x-li-page-instance": self.m_x_li_page_instance,
            "x-li-pem-metadata": self.m_x_li_pem_metadata,
            "x-li-track": self.m_x_li_track,
            "x-restli-protocol-version": self.m_x_restli_protocol_version,
        }
    
