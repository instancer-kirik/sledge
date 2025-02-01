import sys
from functools import wraps

def protect_runtime(cls):
    """Class decorator to protect critical methods"""
    protected_methods = [
        '_collect_basic_metrics',
        '_send_metrics',
        'start',
        '_verify_integrity'
    ]
    
    for method_name in protected_methods:
        method = getattr(cls, method_name)
        setattr(cls, method_name, _protect_method(method))
    
    # Prevent further modifications to the class
    cls.__frozen = True
    return cls

def _protect_method(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        # Verify call stack integrity
        frame = sys._getframe(1)
        if not _verify_call_stack(frame):
            raise SecurityError("Invalid call stack detected")
            
        return method(*args, **kwargs)
    return wrapper

def _verify_call_stack(frame):
    """Verify the integrity of the call stack"""
    while frame:
        # Check if code is coming from our trusted modules
        if not frame.f_code.co_filename.startswith(TRUSTED_PATHS):
            return False
        frame = frame.f_back
    return True

class SecurityError(Exception):
    pass 