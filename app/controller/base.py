import requests
import random as r

# exceptions
class InvalidCredentials(Exception):
    pass

class Base:
    def __init__(self, headers: dict = None, cookies: dict = None):
        self.m_headers = None
        self.m_cookies = None
        self.m_session = requests.Session()
        self.m_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        ]

        if headers is not None:
            self.m_headers = headers
        else:
            raise InvalidCredentials("No headers provided")

        if cookies is not None:
            self.m_cookies = cookies
        else:
            raise InvalidCredentials("No cookies provided")
        
        self.m_session.headers.update(self.m_headers)
        self.m_session.cookies.update(self.m_cookies)

    def get_user_agent(self) -> str:
        return r.choice(self.m_user_agents)