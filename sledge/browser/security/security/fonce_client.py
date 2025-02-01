import aiohttp
import asyncio
from typing import Dict, Optional

class FonceClient:
    def __init__(self, base_url: str = "http://localhost:4000"):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()

    async def check_url(self, url: str) -> Dict:
        async with self.session.post(
            f"{self.base_url}/api/defense/check_url",
            json={"url": url}
        ) as response:
            return await response.json()

    async def report_threat(self, threat_type: str, data: Dict) -> None:
        await self.session.post(
            f"{self.base_url}/api/defense/report_threat",
            json={
                "type": threat_type,
                "data": data
            }
        )

    async def check_privacy(self, request_data: Dict) -> Dict:
        async with self.session.post(
            f"{self.base_url}/api/defense/privacy_check",
            json={"request_data": request_data}
        ) as response:
            return await response.json()

    async def close(self):
        await self.session.close()
