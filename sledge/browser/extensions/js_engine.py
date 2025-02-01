from typing import Dict, Any
from PyQt6.QtQml import QJSEngine, QJSValue
from PyQt6.QtCore import QObject, pyqtSlot

class JSBridge(QObject):
    """Bridge between Python and JavaScript"""
    
    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        
    @pyqtSlot(str, str, result=QJSValue)
    def invoke_api(self, api_name: str, method_name: str, *args) -> Any:
        """Invoke a browser API method from JavaScript"""
        try:
            api = self.runtime.apis.get(api_name)
            if not api:
                raise ValueError(f"API {api_name} not found")
                
            method = getattr(api, method_name, None)
            if not method:
                raise ValueError(f"Method {method_name} not found in {api_name}")
                
            result = method(*args)
            return self._convert_to_js(result)
        except Exception as e:
            print(f"Error invoking API: {e}")
            return QJSValue("undefined")

    def _convert_to_js(self, value: Any) -> QJSValue:
        """Convert Python values to JavaScript values"""
        if isinstance(value, (dict, list)):
            return self.runtime.engine.toScriptValue(value)
        return value

class JSEngine:
    """JavaScript execution engine for extensions"""
    
    def __init__(self, runtime):
        self.runtime = runtime
        self.engine = QJSEngine()
        self.bridge = JSBridge(runtime)
        
        # Add bridge to JS environment
        self.engine.globalObject().setProperty(
            "sledgeBridge", 
            self.engine.newQObject(self.bridge)
        )
        
        # Initialize browser API proxies
        self._init_api_proxies()
        
    def _init_api_proxies(self):
        """Initialize JavaScript proxies for browser APIs"""
        proxy_script = """
        const browser = {
            tabs: new Proxy({}, {
                get: (target, prop) => {
                    return (...args) => sledgeBridge.invoke_api('tabs', prop, ...args);
                }
            }),
            windows: new Proxy({}, {
                get: (target, prop) => {
                    return (...args) => sledgeBridge.invoke_api('windows', prop, ...args);
                }
            }),
            storage: {
                local: new Proxy({}, {
                    get: (target, prop) => {
                        return (...args) => sledgeBridge.invoke_api('storage', prop, ...args);
                    }
                })
            },
            webRequest: new Proxy({}, {
                get: (target, prop) => {
                    return (...args) => sledgeBridge.invoke_api('webRequest', prop, ...args);
                }
            }),
            contextMenus: new Proxy({}, {
                get: (target, prop) => {
                    return (...args) => sledgeBridge.invoke_api('contextMenus', prop, ...args);
                }
            })
        };
        
        // Chrome API compatibility
        const chrome = browser;
        """
        self.engine.evaluate(proxy_script)
        
    def execute_script(self, script: str, context: Dict[str, Any] = None):
        """Execute a JavaScript script in the extension context"""
        try:
            # Add context variables
            if context:
                for key, value in context.items():
                    self.engine.globalObject().setProperty(
                        key, 
                        self.engine.toScriptValue(value)
                    )
            
            # Execute the script
            result = self.engine.evaluate(script)
            
            if result.isError():
                print(f"JavaScript error: {result.toString()}")
                return None
                
            return result.toVariant()
            
        except Exception as e:
            print(f"Error executing script: {e}")
            return None
            
    def register_callback(self, name: str, callback):
        """Register a Python callback function in JavaScript"""
        self.engine.globalObject().setProperty(
            name,
            self.engine.newQObject(callback)
        ) 