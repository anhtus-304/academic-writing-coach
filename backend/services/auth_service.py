from urllib.parse import urlencode
from config import settings
import httpx

class GoogleAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id or "",
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": state
        }
        return f"{self.authorization_endpoint}?{urlencode(params)}"

    async def fetch_token(self, code: str) -> dict:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_endpoint, data=data)
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()