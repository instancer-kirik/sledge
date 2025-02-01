# class BrowserMonitor:
#     """Minimal browser security monitoring"""
    
#     def __init__(self, browser_id: str, fonce_client: FonceClient):
#         self.browser_id = browser_id
#         self.fonce = fonce_client
#         self._event_buffer = []
        
#     async def monitor_request(self, request):
#         """Monitor only security-relevant requests"""
#         if self._should_check_request(request):
#             await self.fonce.check_url(request.url)
            
#     def _should_check_request(self, request) -> bool:
#         """Quick check if request needs security verification"""
#         # Only check main document loads and suspicious patterns
#         return (
#             request.resource_type == "document" or
#             any(pattern in request.url for pattern in SUSPICIOUS_PATTERNS)
#         ) 