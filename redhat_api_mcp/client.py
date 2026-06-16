import os
from typing import Optional, Dict
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()


class RedHatAPI:
    """Red Hat API client with authentication and request handling."""

    def __init__(self):
        self.base_url = os.getenv("RH_API_BASE_URL", "https://access.redhat.com")
        self.sso_url = os.getenv(
            "RH_SSO_URL",
            "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        )
        self.offline_token = os.getenv("RH_API_OFFLINE_TOKEN")
        if not self.offline_token:
            raise ValueError("RH_API_OFFLINE_TOKEN environment variable is required")

        self.access_token = None
        self.token_expiry = None

    async def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        async with httpx.AsyncClient() as client:
            payload = {
                "grant_type": "refresh_token",
                "client_id": "rhsm-api",
                "refresh_token": self.offline_token,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = await client.post(self.sso_url, data=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            self.token_expiry = datetime.now() + timedelta(seconds=data["expires_in"] - 60)

            return self.access_token

    async def make_request(self, method: str, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """Make an authenticated request to the Red Hat API."""
        token = await self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(url, headers=headers, params=params)
            elif method.lower() == "post":
                response = await client.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()

            if "application/json" in response.headers.get("content-type", ""):
                return response.json()
            return {"content": response.text}
