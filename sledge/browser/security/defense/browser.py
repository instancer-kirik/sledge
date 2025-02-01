# from ..defense.event_handler import DefenseEventHandler
# from ..defense.fonce_client import FonceClient

# class Browser:
#     def __init__(self):
#         self.fonce = FonceClient()
#         self.defense = DefenseEventHandler(self.fonce)
        
#     async def start(self):
#         await self.defense.start()

#     async def navigate(self, url: str):
#         # Check URL before navigation
#         await self.defense.handle_event("security_check", {"url": url})
        
#         # Continue with navigation if not blocked
#         # ... rest of navigation logic

#     async def handle_request(self, request):
#         # Check request for suspicious patterns
#         await self.defense.handle_event("suspicious_request", {
#             "url": request.url,
#             "method": request.method,
#             "headers": dict(request.headers)
#         })
        
#         # Continue with request if not blocked
#         # ... rest of request handling 