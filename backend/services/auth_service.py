from authlib.integrations.httpx_client import AsyncOAuth2Client
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
        client = AsyncOAuth2Client(self.client_id, self.client_secret, redirect_uri=self.redirect_uri)
        uri, _ = client.create_authorization_url(
            self.authorization_endpoint,
            state=state,
            scope=["openid", "email", "profile"],
            access_type="offline",
            prompt="select_account"
        )
        return uri

    async def fetch_token(self, code: str) -> dict:
        async with AsyncOAuth2Client(self.client_id, self.client_secret, redirect_uri=self.redirect_uri) as client:
            token = await client.fetch_token(
                self.token_endpoint,
                code=code,
                grant_type="authorization_code"
            )
            return token

    async def get_user_info(self, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()