import requests
from typing import Optional
import logging


class AKCClient:
    """HTTP client for AKC (Agent Knowledge Collective) Phase 1 REST API.

    Handles all HTTP communication with the AKC service, including:
    - Health checks
    - Pattern queries
    - Outcome recording
    - Statistics retrieval

    All methods catch exceptions and return safe defaults without raising.
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout_sec: float = 0.15):
        """Initialize AKC client.

        Args:
            base_url: Base URL of AKC service
            timeout_sec: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_sec
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

    def is_available(self) -> bool:
        """Check if AKC service is available.

        Performs HEAD request to /akc/v1/health with 50ms timeout.

        Returns:
            True if service responds with 200, False on any error.
        """
        try:
            url = f"{self.base_url}/akc/v1/health"
            response = self.session.head(url, timeout=0.05)
            response.raise_for_status()
            return True
        except requests.exceptions.Timeout:
            self.logger.warning("AKC health check timeout")
            return False
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"AKC connection error: {e}")
            return False
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"AKC health check failed: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"Unexpected error in is_available: {e}")
            return False

    def query_patterns(self, task_id: str, entity: str, component: str) -> list[dict]:
        """Query AKC for relevant patterns.

        Args:
            task_id: Task identifier
            entity: Entity name (e.g. 'player', 'enemy')
            component: Component name (e.g. 'movement', 'behavior')

        Returns:
            List of pattern dictionaries, or [] on any error.
        """
        try:
            url = f"{self.base_url}/akc/v1/query"
            payload = {
                "task_id": task_id,
                "entity": entity,
                "component": component
            }
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Log latency if header present
            if "X-AKC-Query-Latency-Ms" in response.headers:
                latency = response.headers.get("X-AKC-Query-Latency-Ms")
                self.logger.debug(f"AKC query latency: {latency}ms")

            # Ensure we return a list
            if isinstance(data, dict) and "patterns" in data:
                return data.get("patterns", [])
            elif isinstance(data, list):
                return data
            else:
                return []
        except requests.exceptions.Timeout:
            self.logger.warning(f"AKC query timeout for task {task_id}")
            return []
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"AKC connection error during query: {e}")
            return []
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"AKC query failed: {e}")
            return []
        except (ValueError, KeyError) as e:
            self.logger.warning(f"AKC response parsing error: {e}")
            return []
        except Exception as e:
            self.logger.warning(f"Unexpected error in query_patterns: {e}")
            return []

    def record_outcome(self, task_result: dict) -> dict:
        """Record task outcome in AKC.

        Args:
            task_result: Dictionary containing task result data

        Returns:
            Response dictionary, or {} on any error.
        """
        try:
            url = f"{self.base_url}/akc/v1/record"
            response = self.session.post(url, json=task_result, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Log latency if header present
            if "X-AKC-Query-Latency-Ms" in response.headers:
                latency = response.headers.get("X-AKC-Query-Latency-Ms")
                self.logger.debug(f"AKC record latency: {latency}ms")

            return data if isinstance(data, dict) else {}
        except requests.exceptions.Timeout:
            self.logger.warning("AKC record outcome timeout")
            return {}
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"AKC connection error during record: {e}")
            return {}
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"AKC record outcome failed: {e}")
            return {}
        except (ValueError, TypeError) as e:
            self.logger.warning(f"AKC outcome response parsing error: {e}")
            return {}
        except Exception as e:
            self.logger.warning(f"Unexpected error in record_outcome: {e}")
            return {}

    def get_stats(self) -> dict:
        """Retrieve AKC statistics.

        Returns:
            Statistics dictionary, or {} on any error.
        """
        try:
            url = f"{self.base_url}/akc/v1/stats"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Log latency if header present
            if "X-AKC-Query-Latency-Ms" in response.headers:
                latency = response.headers.get("X-AKC-Query-Latency-Ms")
                self.logger.debug(f"AKC stats latency: {latency}ms")

            return data if isinstance(data, dict) else {}
        except requests.exceptions.Timeout:
            self.logger.warning("AKC stats request timeout")
            return {}
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"AKC connection error during stats: {e}")
            return {}
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"AKC stats request failed: {e}")
            return {}
        except (ValueError, TypeError) as e:
            self.logger.warning(f"AKC stats response parsing error: {e}")
            return {}
        except Exception as e:
            self.logger.warning(f"Unexpected error in get_stats: {e}")
            return {}
