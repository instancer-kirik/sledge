import psutil
import asyncio
from typing import Dict
import json
import hmac
import hashlib
import os
import time
from cryptography.fernet import Fernet
from sledge.monitoring.protection import protect_runtime
import socket
import sys
import traceback
from sledge.client.fonce import FonceClient
from sledge.utils.logger import Logger

class LightweightAgent:
    """Minimal monitoring agent with low overhead"""
    
    def __init__(self, node_id: str, fonce_url: str):
        self.node_id = node_id
        self.fonce = FonceClient(fonce_url)
        self.running = False
        self._metrics_buffer = []
        self._compromise_attempts = []
        
    async def start(self):
        self.running = True
        await self.fonce.register_node(
            self.node_id, 
            "agent",
            self._get_basic_info()
        )
        await self._monitoring_loop()
        
    async def stop(self):
        self.running = False
        
    async def _monitoring_loop(self):
        while self.running:
            try:
                # Collect minimal metrics
                metrics = self._collect_basic_metrics()
                
                # Buffer metrics
                self._metrics_buffer.append(metrics)
                
                # Send when buffer reaches size or timeout
                if len(self._metrics_buffer) >= 10:
                    await self._send_metrics()
                    
                await asyncio.sleep(5)  # Reduced frequency
                
            except Exception as e:
                Logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)  # Back off on error
                
    def _collect_basic_metrics(self) -> Dict:
        """Collect only essential metrics"""
        return {
            "cpu": psutil.cpu_percent(interval=None),  # Non-blocking
            "memory": psutil.virtual_memory().percent,
            "timestamp": int(time.time())
        }
        
    def _get_basic_info(self) -> Dict:
        """Basic system info, collected once"""
        return {
            "hostname": socket.gethostname(),
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "boot_time": psutil.boot_time()
        }

    def _log_compromise_attempt(self, details: Dict):
        """Log attempted compromises for analysis"""
        attempt = {
            "timestamp": time.time(),
            "details": details,
            "stack_trace": traceback.format_stack(),
            "process_info": {
                "pid": os.getpid(),
                "ppid": os.getppid(),
                "user": os.getlogin(),
                "cwd": os.getcwd()
            }
        }
        self._compromise_attempts.append(attempt)
        
        # Report if we have multiple attempts
        if len(self._compromise_attempts) >= 3:
            asyncio.create_task(
                self.fonce.report_threat(
                    "multiple_compromise_attempts",
                    {
                        "agent_id": self.node_id,
                        "attempts": self._compromise_attempts[-3:],
                        "total_attempts": len(self._compromise_attempts)
                    }
                )
            )

@protect_runtime
class SecureAgent(LightweightAgent):
    def __init__(self, node_id: str, fonce_url: str, hmac_key: bytes):
        super().__init__(node_id, fonce_url)
        self.hmac_key = hmac_key
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Integrity checking
        self._code_hash = self._calculate_code_hash()
        self._last_integrity_check = time.time()
        
    async def _send_metrics(self):
        if not self._metrics_buffer or not self._verify_integrity():
            return
            
        timestamp = int(time.time())
        payload = {
            "metrics": self._metrics_buffer,
            "timestamp": timestamp,
            "agent_id": self.node_id,
            "integrity": self._code_hash
        }
        
        # Sign the payload
        signature = self._sign_payload(payload)
        
        # Encrypt sensitive data
        encrypted_metrics = self.cipher_suite.encrypt(
            json.dumps(self._metrics_buffer).encode()
        )
        
        await self.fonce.report_metrics(
            self.node_id,
            {
                "data": encrypted_metrics,
                "timestamp": timestamp,
                "signature": signature,
                "integrity": self._code_hash
            }
        )
        self._metrics_buffer = []
        
    def _sign_payload(self, payload: dict) -> str:
        message = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(
            self.hmac_key,
            message,
            hashlib.sha256
        ).hexdigest()
        
    def _verify_integrity(self) -> bool:
        # Check if our code has been modified
        current_hash = self._calculate_code_hash()
        if current_hash != self._code_hash:
            self._report_compromise("code_modified")
            return False
            
        # Check for suspicious modifications
        if not self._check_runtime_integrity():
            self._report_compromise("runtime_modified")
            return False
            
        return True
        
    def _calculate_code_hash(self) -> str:
        """Calculate hash of our own code"""
        try:
            with open(__file__, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None
            
    def _check_runtime_integrity(self) -> bool:
        """Check for runtime tampering"""
        # Check if critical functions have been monkey-patched
        original_funcs = [
            self._collect_basic_metrics,
            self._send_metrics,
            self.start
        ]
        
        return all(
            not self._is_monkey_patched(func)
            for func in original_funcs
        )
        
    def _is_monkey_patched(self, func) -> bool:
        """Check if a function has been modified"""
        return hasattr(func, '__wrapped__')
        
    def _report_compromise(self, reason: str):
        """Report potential compromise to Fonce"""
        try:
            details = {
                "agent_id": self.node_id,
                "reason": reason,
                "timestamp": time.time(),
                "process_info": {
                    "pid": os.getpid(),
                    "ppid": os.getppid(),
                    "user": os.getlogin(),
                    "cwd": os.getcwd(),
                    "cmdline": sys.argv,
                    "env_vars": {k: v for k, v in os.environ.items() 
                               if not k.lower().startswith(('key', 'secret', 'token', 'pass'))}
                },
                "system_info": self._get_basic_info()
            }
            
            self._log_compromise_attempt(details)
            asyncio.create_task(
                self.fonce.report_threat(
                    "agent_compromise",
                    details
                )
            )
        except Exception:
            pass  # Don't raise if we can't report