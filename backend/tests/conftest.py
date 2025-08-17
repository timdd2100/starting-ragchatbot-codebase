import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator
from config import Config
from models import Course, CourseChunk, Lesson
from rag_system import RAGSystem
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults, VectorStore


@pytest.fixture
def temp_chroma_path():
    """Create a temporary directory for ChromaDB during tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_chroma_path):
    """Test configuration with temporary paths and mock API key"""
    config = Config()
    config.CHROMA_PATH = temp_chroma_path
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.MAX_RESULTS = 3  # Smaller for testing
    return config


@pytest.fixture
def sample_course():
    """Sample course data for testing"""
    lessons = [
        Lesson(
            lesson_number=1,
            title="Introduction to Python",
            lesson_link="https://example.com/lesson1",
        ),
        Lesson(
            lesson_number=2,
            title="Variables and Data Types",
            lesson_link="https://example.com/lesson2",
        ),
        Lesson(
            lesson_number=3,
            title="Control Structures",
            lesson_link="https://example.com/lesson3",
        ),
    ]
    return Course(
        title="Python Fundamentals",
        course_link="https://example.com/course",
        instructor="Jane Doe",
        lessons=lessons,
    )


@pytest.fixture
def sample_course_chunks(sample_course):
    """Sample course chunks for testing"""
    chunks = [
        CourseChunk(
            content="Python is a high-level programming language. It's great for beginners.",
            course_title="Python Fundamentals",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="Variables in Python can store different types of data like strings and numbers.",
            course_title="Python Fundamentals",
            lesson_number=2,
            chunk_index=1,
        ),
        CourseChunk(
            content="Control structures like if statements help control program flow.",
            course_title="Python Fundamentals",
            lesson_number=3,
            chunk_index=2,
        ),
    ]
    return chunks


@pytest.fixture
def mock_vector_store():
    """Mock vector store for isolated testing"""
    mock_store = Mock(spec=VectorStore)

    # Default successful search result
    mock_store.search.return_value = SearchResults(
        documents=["Python is a high-level programming language."],
        metadata=[
            {
                "course_title": "Python Fundamentals",
                "lesson_number": 1,
                "chunk_index": 0,
            }
        ],
        distances=[0.1],
        error=None,
    )

    return mock_store


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for AI testing"""
    mock_client = Mock()

    # Mock successful response without tool use
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [Mock(text="Here's the answer to your question.")]
    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_anthropic_client_with_tools():
    """Mock Anthropic client that uses tools"""
    mock_client = Mock()

    # Mock tool use response
    mock_tool_response = Mock()
    mock_tool_response.stop_reason = "tool_use"

    # Mock tool use content
    mock_tool_content = Mock()
    mock_tool_content.type = "tool_use"
    mock_tool_content.name = "search_course_content"
    mock_tool_content.id = "tool_123"
    mock_tool_content.input = {"query": "test query"}

    mock_tool_response.content = [mock_tool_content]

    # Mock final response after tool execution
    mock_final_response = Mock()
    mock_final_response.stop_reason = "end_turn"
    mock_final_response.content = [
        Mock(text="Based on the search results, here's the answer.")
    ]

    # Configure client to return tool response first, then final response
    mock_client.messages.create.side_effect = [mock_tool_response, mock_final_response]

    return mock_client


@pytest.fixture
def course_search_tool(mock_vector_store):
    """CourseSearchTool with mocked vector store"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def tool_manager(course_search_tool):
    """ToolManager with registered CourseSearchTool"""
    manager = ToolManager()
    manager.register_tool(course_search_tool)
    return manager


@pytest.fixture
def mock_ai_generator():
    """Mock AI generator for integration testing"""
    mock_ai = Mock(spec=AIGenerator)
    mock_ai.generate_response.return_value = "Test response from AI"
    return mock_ai


@pytest.fixture
def test_app():
    """Create a test FastAPI app without static file mounting for API testing"""
    from typing import List, Optional

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel

    # Create test app
    app = FastAPI(title="Course Materials RAG System Test")

    # Add middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models for request/response
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    return app, QueryRequest, QueryResponse, CourseStats


@pytest.fixture
def mock_rag_system():
    """Mock RAG system for API testing"""
    mock_rag = Mock()
    mock_rag.query.return_value = ("Test answer", ["Test source 1", "Test source 2"])
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Fundamentals", "Advanced Python"],
    }
    mock_rag.session_manager.create_session.return_value = "test-session-id"
    return mock_rag


@pytest.fixture
def test_client(test_app, mock_rag_system):
    """Create a test client with API endpoints and mocked dependencies"""
    from fastapi import HTTPException
    from fastapi.testclient import TestClient

    app, QueryRequest, QueryResponse, CourseStats = test_app

    # Define API endpoints inline to avoid import issues
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            formatted_sources = []
            if sources:
                for source in sources:
                    if isinstance(source, dict):
                        formatted_sources.append(f"{source.get('text', '')}")
                    else:
                        formatted_sources.append(str(source))

            return QueryResponse(
                answer=answer, sources=formatted_sources, session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return TestClient(app)


# Helper functions for creating test data


def create_search_results(
    documents: List[str],
    course_title: str = "Test Course",
    lesson_numbers: List[int] = None,
    error: str = None,
) -> SearchResults:
    """Helper to create SearchResults for testing"""
    if lesson_numbers is None:
        lesson_numbers = [1] * len(documents)

    metadata = [
        {"course_title": course_title, "lesson_number": lesson_num, "chunk_index": i}
        for i, lesson_num in enumerate(lesson_numbers)
    ]

    return SearchResults(
        documents=documents,
        metadata=metadata,
        distances=[0.1] * len(documents),
        error=error,
    )


def create_empty_search_results(error: str = None) -> SearchResults:
    """Helper to create empty SearchResults for testing"""
    return SearchResults(documents=[], metadata=[], distances=[], error=error)
