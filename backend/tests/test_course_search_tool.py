from unittest.mock import Mock, patch

import pytest

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults

from .conftest import create_empty_search_results, create_search_results


class TestCourseSearchTool:
    """Test CourseSearchTool execute method and functionality"""

    def test_get_tool_definition(self, course_search_tool):
        """Test that tool definition is properly formatted"""
        definition = course_search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert "properties" in definition["input_schema"]
        assert "query" in definition["input_schema"]["properties"]
        assert "required" in definition["input_schema"]
        assert "query" in definition["input_schema"]["required"]

    def test_execute_basic_search_success(self, mock_vector_store):
        """Test successful basic search without filters"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_search_results(
            documents=["Python is a programming language."],
            course_title="Python Fundamentals",
            lesson_numbers=[1],
        )

        # Execute
        result = tool.execute(query="What is Python?")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="What is Python?", course_name=None, lesson_number=None
        )
        assert "[Python Fundamentals - Lesson 1]" in result
        assert "Python is a programming language." in result

    def test_execute_with_course_filter(self, mock_vector_store):
        """Test search with course name filter"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_search_results(
            documents=["Variables store data."],
            course_title="Python Fundamentals",
            lesson_numbers=[2],
        )

        # Execute
        result = tool.execute(query="variables", course_name="Python Fundamentals")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="variables", course_name="Python Fundamentals", lesson_number=None
        )
        assert "[Python Fundamentals - Lesson 2]" in result
        assert "Variables store data." in result

    def test_execute_with_lesson_filter(self, mock_vector_store):
        """Test search with lesson number filter"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_search_results(
            documents=["Control structures guide flow."],
            course_title="Python Fundamentals",
            lesson_numbers=[3],
        )

        # Execute
        result = tool.execute(query="control structures", lesson_number=3)

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="control structures", course_name=None, lesson_number=3
        )
        assert "[Python Fundamentals - Lesson 3]" in result

    def test_execute_with_both_filters(self, mock_vector_store):
        """Test search with both course and lesson filters"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_search_results(
            documents=["Functions encapsulate code."],
            course_title="Python Fundamentals",
            lesson_numbers=[4],
        )

        # Execute
        result = tool.execute(
            query="functions", course_name="Python Fundamentals", lesson_number=4
        )

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="functions", course_name="Python Fundamentals", lesson_number=4
        )

    def test_execute_multiple_results(self, mock_vector_store):
        """Test search returning multiple results"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_search_results(
            documents=[
                "Python is easy to learn.",
                "Python has simple syntax.",
                "Python is versatile.",
            ],
            course_title="Python Fundamentals",
            lesson_numbers=[1, 1, 1],
        )

        # Execute
        result = tool.execute(query="Python benefits")

        # Verify all results are included
        assert "Python is easy to learn." in result
        assert "Python has simple syntax." in result
        assert "Python is versatile." in result
        assert result.count("[Python Fundamentals - Lesson 1]") == 3

    def test_execute_empty_results(self, mock_vector_store):
        """Test search returning no results"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_empty_search_results()

        # Execute
        result = tool.execute(query="nonexistent topic")

        # Verify
        assert result == "No relevant content found."

    def test_execute_empty_results_with_course_filter(self, mock_vector_store):
        """Test search returning no results with course filter"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_empty_search_results()

        # Execute
        result = tool.execute(
            query="nonexistent topic", course_name="Python Fundamentals"
        )

        # Verify
        assert result == "No relevant content found in course 'Python Fundamentals'."

    def test_execute_empty_results_with_lesson_filter(self, mock_vector_store):
        """Test search returning no results with lesson filter"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_empty_search_results()

        # Execute
        result = tool.execute(query="nonexistent topic", lesson_number=5)

        # Verify
        assert result == "No relevant content found in lesson 5."

    def test_execute_empty_results_with_both_filters(self, mock_vector_store):
        """Test search returning no results with both filters"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_empty_search_results()

        # Execute
        result = tool.execute(
            query="nonexistent topic",
            course_name="Python Fundamentals",
            lesson_number=5,
        )

        # Verify
        assert (
            result
            == "No relevant content found in course 'Python Fundamentals' in lesson 5."
        )

    def test_execute_with_search_error(self, mock_vector_store):
        """Test handling of search errors"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_empty_search_results(
            error="Database connection failed"
        )

        # Execute
        result = tool.execute(query="test query")

        # Verify
        assert result == "Database connection failed"

    def test_execute_tracks_sources(self, mock_vector_store):
        """Test that sources are tracked for UI display"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.search.return_value = create_search_results(
            documents=["Test content"], course_title="Test Course", lesson_numbers=[2]
        )

        # Execute
        tool.execute(query="test")

        # Verify sources were tracked
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Test Course - Lesson 2"

    def test_execute_sources_without_lesson(self, mock_vector_store):
        """Test source tracking when lesson number is None"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)

        # Create results with lesson_number as None
        results = SearchResults(
            documents=["Test content"],
            metadata=[
                {"course_title": "Test Course", "lesson_number": None, "chunk_index": 0}
            ],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = results

        # Execute
        tool.execute(query="test")

        # Verify sources tracked correctly
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Test Course"

    def test_format_results_with_lesson_links(self, mock_vector_store):
        """Test that lesson links are retrieved and included in sources"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson2"

        results = create_search_results(
            documents=["Test content"], course_title="Test Course", lesson_numbers=[2]
        )
        mock_vector_store.search.return_value = results

        # Execute
        tool.execute(query="test")

        # Verify lesson link was retrieved
        mock_vector_store.get_lesson_link.assert_called_once_with("Test Course", 2)
        assert tool.last_sources[0]["link"] == "https://example.com/lesson2"

    def test_missing_metadata_fields(self, mock_vector_store):
        """Test handling of missing metadata fields"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)

        # Results with missing metadata fields
        results = SearchResults(
            documents=["Test content"],
            metadata=[{}],  # Empty metadata
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = results

        # Execute
        result = tool.execute(query="test")

        # Verify it handles missing fields gracefully
        assert "[unknown]" in result
        assert "Test content" in result


class TestToolManager:
    """Test ToolManager functionality with CourseSearchTool"""

    def test_register_tool(self, course_search_tool):
        """Test registering a tool"""
        manager = ToolManager()
        manager.register_tool(course_search_tool)

        assert "search_course_content" in manager.tools
        assert len(manager.get_tool_definitions()) == 1

    def test_execute_tool(self, mock_vector_store):
        """Test executing a registered tool"""
        # Setup
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        mock_vector_store.search.return_value = create_search_results(
            documents=["Test result"], course_title="Test Course"
        )

        # Execute
        result = manager.execute_tool("search_course_content", query="test query")

        # Verify
        assert "Test result" in result

    def test_execute_nonexistent_tool(self, tool_manager):
        """Test executing a tool that doesn't exist"""
        result = tool_manager.execute_tool("nonexistent_tool", query="test")
        assert result == "Tool 'nonexistent_tool' not found"

    def test_get_last_sources(self, mock_vector_store):
        """Test retrieving last sources from tool manager"""
        # Setup
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Set up sources in tool
        tool.last_sources = [{"text": "Test Course", "link": None}]

        # Execute
        sources = manager.get_last_sources()

        # Verify
        assert len(sources) == 1
        assert sources[0]["text"] == "Test Course"

    def test_reset_sources(self, mock_vector_store):
        """Test resetting sources in tool manager"""
        # Setup
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Set up sources in tool
        tool.last_sources = [{"text": "Test Course", "link": None}]

        # Execute
        manager.reset_sources()

        # Verify
        assert tool.last_sources == []
