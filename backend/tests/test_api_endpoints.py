import json
from unittest.mock import Mock, patch

import pytest


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for /api/query endpoint"""

    def test_query_with_session_id(self, test_client, mock_rag_system):
        """Test query endpoint with provided session ID"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "existing-session"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Test answer"
        assert data["sources"] == ["Test source 1", "Test source 2"]
        assert data["session_id"] == "existing-session"

        mock_rag_system.query.assert_called_once_with(
            "What is Python?", "existing-session"
        )

    def test_query_without_session_id(self, test_client, mock_rag_system):
        """Test query endpoint without session ID (should create new session)"""
        response = test_client.post("/api/query", json={"query": "What is Python?"})

        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Test answer"
        assert data["sources"] == ["Test source 1", "Test source 2"]
        assert data["session_id"] == "test-session-id"

        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with(
            "What is Python?", "test-session-id"
        )

    def test_query_with_dict_sources(self, test_client, mock_rag_system):
        """Test query endpoint with dictionary-formatted sources"""
        mock_rag_system.query.return_value = (
            "Test answer",
            [{"text": "Source text 1"}, {"text": "Source text 2"}],
        )

        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "test-session"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Test answer"
        assert data["sources"] == ["Source text 1", "Source text 2"]
        assert data["session_id"] == "test-session"

    def test_query_with_empty_sources(self, test_client, mock_rag_system):
        """Test query endpoint with no sources"""
        mock_rag_system.query.return_value = ("Test answer", [])

        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "test-session"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Test answer"
        assert data["sources"] == []
        assert data["session_id"] == "test-session"

    def test_query_missing_query_field(self, test_client):
        """Test query endpoint with missing query field"""
        response = test_client.post("/api/query", json={"session_id": "test-session"})

        assert response.status_code == 422  # Validation error

    def test_query_empty_query(self, test_client):
        """Test query endpoint with empty query"""
        response = test_client.post(
            "/api/query", json={"query": "", "session_id": "test-session"}
        )

        assert response.status_code == 200

    def test_query_rag_system_error(self, test_client, mock_rag_system):
        """Test query endpoint when RAG system raises exception"""
        mock_rag_system.query.side_effect = Exception("RAG system error")

        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "test-session"},
        )

        assert response.status_code == 500
        assert "RAG system error" in response.json()["detail"]

    def test_query_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for /api/courses endpoint"""

    def test_get_courses_success(self, test_client, mock_rag_system):
        """Test successful retrieval of course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Python Fundamentals", "Advanced Python"]

        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_empty_analytics(self, test_client, mock_rag_system):
        """Test courses endpoint with empty analytics"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_rag_system_error(self, test_client, mock_rag_system):
        """Test courses endpoint when RAG system raises exception"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        assert "Analytics error" in response.json()["detail"]

    def test_get_courses_no_parameters(self, test_client):
        """Test courses endpoint doesn't accept parameters"""
        response = test_client.get("/api/courses?param=value")

        assert response.status_code == 200  # Should ignore parameters


@pytest.mark.api
class TestContentTypeHandling:
    """Test suite for content type handling"""

    def test_query_with_form_data(self, test_client):
        """Test query endpoint rejects form data"""
        response = test_client.post("/api/query", data={"query": "What is Python?"})

        assert response.status_code == 422

    def test_query_with_correct_content_type(self, test_client):
        """Test query endpoint with explicit JSON content type"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?"},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200


@pytest.mark.api
class TestResponseValidation:
    """Test suite for response model validation"""

    def test_query_response_structure(self, test_client):
        """Test that query response matches expected structure"""
        response = test_client.post(
            "/api/query", json={"query": "What is Python?", "session_id": "test"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify data types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_courses_response_structure(self, test_client):
        """Test that courses response matches expected structure"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify data types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])


@pytest.mark.api
class TestCORSAndMiddleware:
    """Test suite for CORS and middleware functionality"""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present in responses"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_options_request(self, test_client):
        """Test CORS preflight OPTIONS request"""
        response = test_client.options("/api/query")

        # Should handle OPTIONS request without error
        assert response.status_code in [200, 405]  # Some test clients may return 405


@pytest.mark.integration
class TestEndToEndScenarios:
    """Integration tests for realistic usage scenarios"""

    def test_query_then_courses_workflow(self, test_client, mock_rag_system):
        """Test a typical workflow: query then get courses"""
        # First, make a query
        query_response = test_client.post(
            "/api/query", json={"query": "What courses are available?"}
        )
        assert query_response.status_code == 200

        # Then get course statistics
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200

        # Verify both calls worked
        query_data = query_response.json()
        courses_data = courses_response.json()

        assert query_data["answer"] == "Test answer"
        assert courses_data["total_courses"] == 2

    def test_multiple_queries_same_session(self, test_client, mock_rag_system):
        """Test multiple queries with same session ID"""
        session_id = "persistent-session"

        # First query
        response1 = test_client.post(
            "/api/query", json={"query": "What is Python?", "session_id": session_id}
        )
        assert response1.status_code == 200
        assert response1.json()["session_id"] == session_id

        # Second query with same session
        response2 = test_client.post(
            "/api/query",
            json={"query": "Tell me more about variables", "session_id": session_id},
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Verify RAG system was called with correct session ID both times
        assert mock_rag_system.query.call_count == 2
        calls = mock_rag_system.query.call_args_list
        assert calls[0][0][1] == session_id  # Second argument is session_id
        assert calls[1][0][1] == session_id
