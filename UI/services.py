# services.py
import os
from typing import List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException, Timeout
from urllib3.util.retry import Retry

from config import EDGE_TYPES, EDGE_TYPE_NAMES, BACKEND_BASE_URL, BACKEND_TIMEOUT

class BackendError(Exception):
    pass

class NotFoundError(BackendError):
    pass

class BackendClient:
    
    def __init__(self, base_url: str | None = None, timeout: int = BACKEND_TIMEOUT, max_retries: int = 2):
        self.base_url = (base_url or BACKEND_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

        retries = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_graph(self, source: str) -> Dict[str, Any]:
        if not source or not source.strip():
            raise ValueError("source must be a non-empty string")
        
        url = f"{self.base_url}/api/graph"
        try:
            resp = self.session.get(url, params={"technology": source}, timeout=self.timeout)
        except Timeout as e:
            raise BackendError("request timed out (server took too long to respond)") from e
        except RequestException as e:
            raise BackendError("network error (failed to connect to backend)") from e

        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError as e:
                raise BackendError("invalid JSON response from backend") from e
            
            if not isinstance(data, dict) or "nodes" not in data or "edges" not in data:
                raise BackendError("unexpected response format from backend (missing nodes or edges)")
            
            return data
        
        if resp.status_code == 404:
            raise NotFoundError(f"graph not found for source '{source}'")
        
        error_msg = f"backend returned status {resp.status_code}"
        if resp.text:
            error_msg += f": {resp.text[:200]}"
        raise BackendError(error_msg)

    def get_available_connection_types(self) -> List[str]:
        return EDGE_TYPES
    
    def get_connection_type_display_name(self, type_code: str) -> str:
        return EDGE_TYPE_NAMES.get(type_code, type_code)