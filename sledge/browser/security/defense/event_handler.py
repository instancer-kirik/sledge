from typing import Dict, Any
import asyncio
from .fonce_client import FonceClient

class DefenseEventHandler:
    def __init__(self, fonce_client: FonceClient):
        self.fonce = fonce_client
        self.event_queue = asyncio.Queue()
        self.running = False

    async def start(self):
        self.running = True
        await self.process_events()

    async def stop(self):
        self.running = False

    async def handle_event(self, event_type: str, data: Dict[str, Any]):
        await self.event_queue.put({
            "type": event_type,
            "data": data
        })

    async def process_events(self):
        while self.running:
            try:
                event = await self.event_queue.get()
                
                if event["type"] == "suspicious_request":
                    await self.fonce.report_threat("suspicious_request", event["data"])
                elif event["type"] == "privacy_violation":
                    await self.fonce.check_privacy(event["data"])
                elif event["type"] == "security_check":
                    result = await self.fonce.check_url(event["data"]["url"])
                    if result["status"] == "blocked":
                        # Handle blocked URL
                        pass

                self.event_queue.task_done()
            except Exception as e:
                print(f"Error processing event: {e}")
                # Could add retry logic here 