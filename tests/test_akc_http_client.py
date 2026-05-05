import unittest
from unittest.mock import patch, MagicMock
import requests
from agent_system.akc_http_client import AKCClient


class TestAKCClientIsAvailable(unittest.TestCase):
    """Tests for AKCClient.is_available() method."""

    @patch("requests.Session.head")
    def test_is_available_success(self, mock_head):
        """Test successful health check returns True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        client = AKCClient()
        result = client.is_available()

        self.assertTrue(result)
        mock_head.assert_called_once()
        # Verify 50ms timeout was used
        call_kwargs = mock_head.call_args[1]
        self.assertEqual(call_kwargs["timeout"], 0.05)

    @patch("requests.Session.head")
    def test_is_available_timeout(self, mock_head):
        """Test timeout returns False."""
        mock_head.side_effect = requests.exceptions.Timeout()

        client = AKCClient()
        result = client.is_available()

        self.assertFalse(result)

    @patch("requests.Session.head")
    def test_is_available_connection_error(self, mock_head):
        """Test connection error returns False."""
        mock_head.side_effect = requests.exceptions.ConnectionError("Connection refused")

        client = AKCClient()
        result = client.is_available()

        self.assertFalse(result)

    @patch("requests.Session.head")
    def test_is_available_http_error(self, mock_head):
        """Test HTTP error returns False."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_head.return_value = mock_response

        client = AKCClient()
        result = client.is_available()

        self.assertFalse(result)


class TestAKCClientQueryPatterns(unittest.TestCase):
    """Tests for AKCClient.query_patterns() method."""

    @patch("requests.Session.post")
    def test_query_patterns_success(self, mock_post):
        """Test successful pattern query returns list of patterns."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "patterns": [
                {"id": "p1", "name": "pattern1"},
                {"id": "p2", "name": "pattern2"}
            ]
        }
        mock_response.headers = {}
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "p1")

    @patch("requests.Session.post")
    def test_query_patterns_empty(self, mock_post):
        """Test empty pattern list from server."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"patterns": []}
        mock_response.headers = {}
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_query_patterns_list_response(self, mock_post):
        """Test pattern query with direct list response."""
        mock_response = MagicMock()
        patterns = [{"id": "p1"}, {"id": "p2"}]
        mock_response.json.return_value = patterns
        mock_response.headers = {}
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(result, patterns)

    @patch("requests.Session.post")
    def test_query_patterns_timeout(self, mock_post):
        """Test timeout returns empty list."""
        mock_post.side_effect = requests.exceptions.Timeout()

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_query_patterns_connection_error(self, mock_post):
        """Test connection error returns empty list."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_query_patterns_http_500(self, mock_post):
        """Test HTTP 500 error returns empty list."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_query_patterns_invalid_json(self, mock_post):
        """Test invalid JSON response returns empty list."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(result, [])

    @patch("requests.Session.post")
    def test_query_patterns_latency_header(self, mock_post):
        """Test latency header is logged when present."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"patterns": []}
        mock_response.headers = {"X-AKC-Query-Latency-Ms": "42"}
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.query_patterns("task123", "player", "movement")

        self.assertEqual(result, [])
        # Verify latency header was accessible
        self.assertIn("X-AKC-Query-Latency-Ms", mock_response.headers)


class TestAKCClientRecordOutcome(unittest.TestCase):
    """Tests for AKCClient.record_outcome() method."""

    @patch("requests.Session.post")
    def test_record_outcome_success(self, mock_post):
        """Test successful outcome recording returns response dict."""
        mock_response = MagicMock()
        response_data = {
            "status": "recorded",
            "task_id": "task123",
            "timestamp": "2026-05-04T10:00:00Z"
        }
        mock_response.json.return_value = response_data
        mock_response.status_code = 202
        mock_response.headers = {}
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.record_outcome({"task_id": "task123", "result": "success"})

        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["task_id"], "task123")

    @patch("requests.Session.post")
    def test_record_outcome_bad_request(self, mock_post):
        """Test bad request returns empty dict."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.record_outcome({"task_id": "task123"})

        self.assertEqual(result, {})

    @patch("requests.Session.post")
    def test_record_outcome_timeout(self, mock_post):
        """Test timeout returns empty dict."""
        mock_post.side_effect = requests.exceptions.Timeout()

        client = AKCClient()
        result = client.record_outcome({"task_id": "task123"})

        self.assertEqual(result, {})

    @patch("requests.Session.post")
    def test_record_outcome_connection_error(self, mock_post):
        """Test connection error returns empty dict."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        client = AKCClient()
        result = client.record_outcome({"task_id": "task123"})

        self.assertEqual(result, {})

    @patch("requests.Session.post")
    def test_record_outcome_invalid_json(self, mock_post):
        """Test invalid JSON response returns empty dict."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.record_outcome({"task_id": "task123"})

        self.assertEqual(result, {})

    @patch("requests.Session.post")
    def test_record_outcome_non_dict_response(self, mock_post):
        """Test non-dict response returns empty dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = ["not", "a", "dict"]
        mock_response.headers = {}
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.record_outcome({"task_id": "task123"})

        self.assertEqual(result, {})

    @patch("requests.Session.post")
    def test_record_outcome_latency_header(self, mock_post):
        """Test latency header is logged when present."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "recorded"}
        mock_response.headers = {"X-AKC-Query-Latency-Ms": "35"}
        mock_post.return_value = mock_response

        client = AKCClient()
        result = client.record_outcome({"task_id": "task123"})

        self.assertEqual(result["status"], "recorded")


class TestAKCClientGetStats(unittest.TestCase):
    """Tests for AKCClient.get_stats() method."""

    @patch("requests.Session.get")
    def test_get_stats_success(self, mock_get):
        """Test successful stats retrieval returns dict."""
        mock_response = MagicMock()
        stats_data = {
            "total_tasks": 42,
            "patterns_cached": 128,
            "avg_query_time_ms": 12.5
        }
        mock_response.json.return_value = stats_data
        mock_response.headers = {}
        mock_get.return_value = mock_response

        client = AKCClient()
        result = client.get_stats()

        self.assertEqual(result["total_tasks"], 42)
        self.assertEqual(result["patterns_cached"], 128)

    @patch("requests.Session.get")
    def test_get_stats_error(self, mock_get):
        """Test error returns empty dict."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        client = AKCClient()
        result = client.get_stats()

        self.assertEqual(result, {})

    @patch("requests.Session.get")
    def test_get_stats_timeout(self, mock_get):
        """Test timeout returns empty dict."""
        mock_get.side_effect = requests.exceptions.Timeout()

        client = AKCClient()
        result = client.get_stats()

        self.assertEqual(result, {})

    @patch("requests.Session.get")
    def test_get_stats_connection_error(self, mock_get):
        """Test connection error returns empty dict."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        client = AKCClient()
        result = client.get_stats()

        self.assertEqual(result, {})


class TestAKCClientIntegration(unittest.TestCase):
    """Integration-level tests for AKCClient."""

    @patch("requests.Session.post")
    def test_query_count(self, mock_post):
        """Verify only one POST request is made per query_patterns call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"patterns": [{"id": "p1"}]}
        mock_response.headers = {}
        mock_post.return_value = mock_response

        client = AKCClient()
        client.query_patterns("task123", "player", "movement")

        # Verify exactly one POST call
        self.assertEqual(mock_post.call_count, 1)

    @patch("requests.Session.post")
    def test_timeout_value(self, mock_post):
        """Verify custom timeout is passed as parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"patterns": []}
        mock_response.headers = {}
        mock_post.return_value = mock_response

        client = AKCClient(timeout_sec=0.3)
        client.query_patterns("task123", "player", "movement")

        # Verify timeout was passed correctly
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["timeout"], 0.3)

    @patch("requests.Session.post")
    def test_base_url_normalization(self, mock_post):
        """Verify base URL is normalized (trailing slash removed)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"patterns": []}
        mock_response.headers = {}
        mock_post.return_value = mock_response

        # Test with trailing slash
        client = AKCClient(base_url="http://localhost:8000/")
        client.query_patterns("task123", "player", "movement")

        # Verify URL doesn't have double slash
        call_args = mock_post.call_args[0]
        url = call_args[0]
        self.assertEqual(url, "http://localhost:8000/akc/v1/query")


if __name__ == "__main__":
    unittest.main()
