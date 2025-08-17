import os
import shutil
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from config import Config
from rag_system import RAGSystem

from .conftest import create_empty_search_results, create_search_results


class TestRAGSystemInitialization:
    """Test RAG system initialization and component setup"""

    def test_init_components(self, test_config):
        """Test that all components are properly initialized"""
        rag = RAGSystem(test_config)

        # Verify all components exist
        assert rag.document_processor is not None
        assert rag.vector_store is not None
        assert rag.ai_generator is not None
        assert rag.session_manager is not None
        assert rag.tool_manager is not None
        assert rag.search_tool is not None
        assert rag.outline_tool is not None

        # Verify tools are registered
        assert "search_course_content" in rag.tool_manager.tools
        assert "get_course_outline" in rag.tool_manager.tools


class TestRAGSystemDocumentProcessing:
    """Test document processing functionality"""

    def test_add_course_document_success(self, test_config, tmp_path):
        """Test successful course document addition"""
        # Create a test document
        test_doc = tmp_path / "test_course.txt"
        test_doc.write_text(
            """Course Title: Python Fundamentals
Instructor: Jane Doe
Course Link: https://example.com/course

Lesson 1: Introduction to Python
Lesson Link: https://example.com/lesson1

Python is a high-level programming language that is easy to learn.
It has simple syntax and is great for beginners.

Lesson 2: Variables and Data Types
Lesson Link: https://example.com/lesson2

Variables in Python can store different types of data.
You can create variables without declaring their type.
"""
        )

        rag = RAGSystem(test_config)

        # Add the document
        course, chunk_count = rag.add_course_document(str(test_doc))

        # Verify results
        assert course is not None
        assert course.title == "Python Fundamentals"
        assert course.instructor == "Jane Doe"
        assert len(course.lessons) == 2
        assert chunk_count > 0

    def test_add_course_document_file_not_found(self, test_config):
        """Test handling of non-existent file"""
        rag = RAGSystem(test_config)

        course, chunk_count = rag.add_course_document("nonexistent_file.txt")

        assert course is None
        assert chunk_count == 0

    def test_add_course_folder_success(self, test_config, tmp_path):
        """Test adding multiple documents from a folder"""
        # Create test documents
        doc1 = tmp_path / "course1.txt"
        doc1.write_text(
            """Course Title: Python Basics
Instructor: John Smith
Course Link: https://example.com/python

Lesson 1: Getting Started
Lesson Link: https://example.com/python/lesson1

Python is a programming language.
"""
        )

        doc2 = tmp_path / "course2.txt"
        doc2.write_text(
            """Course Title: JavaScript Fundamentals
Instructor: Jane Doe
Course Link: https://example.com/js

Lesson 1: Introduction to JS
Lesson Link: https://example.com/js/lesson1

JavaScript runs in the browser.
"""
        )

        rag = RAGSystem(test_config)

        # Add folder
        total_courses, total_chunks = rag.add_course_folder(str(tmp_path))

        # Verify results
        assert total_courses == 2
        assert total_chunks > 0

    def test_add_course_folder_nonexistent(self, test_config):
        """Test handling of non-existent folder"""
        rag = RAGSystem(test_config)

        total_courses, total_chunks = rag.add_course_folder("nonexistent_folder")

        assert total_courses == 0
        assert total_chunks == 0


class TestRAGSystemQuery:
    """Test query processing functionality"""

    @patch("rag_system.AIGenerator")
    def test_query_success_without_session(self, mock_ai_generator_class, test_config):
        """Test successful query without session management"""
        # Setup mocks
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.return_value = (
            "Python is a programming language."
        )
        mock_ai_generator_class.return_value = mock_ai_generator

        rag = RAGSystem(test_config)
        rag.ai_generator = mock_ai_generator

        # Mock tool manager to return empty sources
        rag.tool_manager.get_last_sources = Mock(return_value=[])
        rag.tool_manager.reset_sources = Mock()

        # Execute query
        response, sources = rag.query("What is Python?")

        # Verify
        assert response == "Python is a programming language."
        assert sources == []

        # Verify AI generator was called correctly
        mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_ai_generator.generate_response.call_args
        assert "What is Python?" in call_args[1]["query"]
        assert call_args[1]["conversation_history"] is None

    @patch("rag_system.AIGenerator")
    def test_query_with_session_management(self, mock_ai_generator_class, test_config):
        """Test query with session management"""
        # Setup mocks
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.return_value = (
            "Variables store data in Python."
        )
        mock_ai_generator_class.return_value = mock_ai_generator

        rag = RAGSystem(test_config)
        rag.ai_generator = mock_ai_generator

        # Mock session manager
        rag.session_manager.get_conversation_history = Mock(
            return_value="Previous conversation context"
        )
        rag.session_manager.add_exchange = Mock()

        # Mock tool manager
        rag.tool_manager.get_last_sources = Mock(return_value=[])
        rag.tool_manager.reset_sources = Mock()

        # Execute query with session
        response, sources = rag.query("What are variables?", session_id="session123")

        # Verify
        assert response == "Variables store data in Python."

        # Verify session management
        rag.session_manager.get_conversation_history.assert_called_once_with(
            "session123"
        )
        rag.session_manager.add_exchange.assert_called_once_with(
            "session123", "What are variables?", "Variables store data in Python."
        )

        # Verify conversation history was passed
        call_args = mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] == "Previous conversation context"

    @patch("rag_system.AIGenerator")
    def test_query_with_sources_from_tools(self, mock_ai_generator_class, test_config):
        """Test query that returns sources from tool usage"""
        # Setup mocks
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.return_value = (
            "Based on the course materials, Python is versatile."
        )
        mock_ai_generator_class.return_value = mock_ai_generator

        rag = RAGSystem(test_config)
        rag.ai_generator = mock_ai_generator

        # Mock tool manager to return sources
        mock_sources = [
            {
                "text": "Python Fundamentals - Lesson 1",
                "link": "https://example.com/lesson1",
            },
            {
                "text": "Python Fundamentals - Lesson 2",
                "link": "https://example.com/lesson2",
            },
        ]
        rag.tool_manager.get_last_sources = Mock(return_value=mock_sources)
        rag.tool_manager.reset_sources = Mock()

        # Execute query
        response, sources = rag.query("What is Python?")

        # Verify
        assert response == "Based on the course materials, Python is versatile."
        assert sources == mock_sources

        # Verify sources were retrieved and reset
        rag.tool_manager.get_last_sources.assert_called_once()
        rag.tool_manager.reset_sources.assert_called_once()

    @patch("rag_system.AIGenerator")
    def test_query_tools_and_tool_manager_passed(
        self, mock_ai_generator_class, test_config
    ):
        """Test that tools and tool manager are passed to AI generator"""
        # Setup mocks
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.return_value = "Response with tools."
        mock_ai_generator_class.return_value = mock_ai_generator

        rag = RAGSystem(test_config)
        rag.ai_generator = mock_ai_generator

        # Mock tool manager
        mock_tool_definitions = [
            {"name": "search_course_content", "description": "Search course content"},
            {"name": "get_course_outline", "description": "Get course outline"},
        ]
        rag.tool_manager.get_tool_definitions = Mock(return_value=mock_tool_definitions)
        rag.tool_manager.get_last_sources = Mock(return_value=[])
        rag.tool_manager.reset_sources = Mock()

        # Execute query
        response, sources = rag.query("What is Python?")

        # Verify tools were passed
        call_args = mock_ai_generator.generate_response.call_args
        assert call_args[1]["tools"] == mock_tool_definitions
        assert call_args[1]["tool_manager"] == rag.tool_manager


class TestRAGSystemAnalytics:
    """Test analytics functionality"""

    def test_get_course_analytics(self, test_config):
        """Test getting course analytics"""
        rag = RAGSystem(test_config)

        # Mock vector store methods
        rag.vector_store.get_course_count = Mock(return_value=5)
        rag.vector_store.get_existing_course_titles = Mock(
            return_value=[
                "Python Fundamentals",
                "JavaScript Basics",
                "Data Science 101",
                "Web Development",
                "Machine Learning",
            ]
        )

        # Execute
        analytics = rag.get_course_analytics()

        # Verify
        assert analytics["total_courses"] == 5
        assert len(analytics["course_titles"]) == 5
        assert "Python Fundamentals" in analytics["course_titles"]


class TestRAGSystemIntegration:
    """Integration tests with real components"""

    def test_end_to_end_with_real_vector_store(
        self, test_config, sample_course, sample_course_chunks
    ):
        """Test end-to-end flow with real vector store but mocked AI"""
        with patch("rag_system.AIGenerator") as mock_ai_generator_class:
            # Setup AI mock
            mock_ai_generator = Mock()
            mock_ai_generator.generate_response.return_value = (
                "Python is a programming language for beginners."
            )
            mock_ai_generator_class.return_value = mock_ai_generator

            rag = RAGSystem(test_config)
            rag.ai_generator = mock_ai_generator

            # Add real course data
            rag.vector_store.add_course_metadata(sample_course)
            rag.vector_store.add_course_content(sample_course_chunks)

            # Execute query - this will use real vector store but mocked AI
            response, sources = rag.query("What is Python?")

            # Verify
            assert response == "Python is a programming language for beginners."

            # Verify AI was called with real tool manager
            mock_ai_generator.generate_response.assert_called_once()
            call_args = mock_ai_generator.generate_response.call_args
            assert call_args[1]["tools"] is not None
            assert call_args[1]["tool_manager"] is not None

    @patch("rag_system.AIGenerator")
    def test_ai_generator_failure_handling(self, mock_ai_generator_class, test_config):
        """Test handling of AI generator failures"""
        # Setup AI mock to raise exception
        mock_ai_generator = Mock()
        mock_ai_generator.generate_response.side_effect = Exception(
            "API connection failed"
        )
        mock_ai_generator_class.return_value = mock_ai_generator

        rag = RAGSystem(test_config)
        rag.ai_generator = mock_ai_generator

        # Execute query and expect exception
        with pytest.raises(Exception, match="API connection failed"):
            rag.query("What is Python?")

    def test_real_document_processing_and_query(self, test_config, tmp_path):
        """Test with real document processing but mocked AI responses"""
        with patch("rag_system.AIGenerator") as mock_ai_generator_class:
            # Setup AI mock
            mock_ai_generator = Mock()
            mock_ai_generator.generate_response.return_value = (
                "Based on the course content, Python is easy to learn."
            )
            mock_ai_generator_class.return_value = mock_ai_generator

            # Create a realistic test document
            test_doc = tmp_path / "python_course.txt"
            test_doc.write_text(
                """Course Title: Introduction to Python Programming
Instructor: Dr. Sarah Johnson
Course Link: https://university.edu/python-course

Lesson 1: Getting Started with Python
Lesson Link: https://university.edu/python-course/lesson1

Python is a high-level, interpreted programming language with dynamic semantics. 
Its high-level built-in data structures, combined with dynamic typing and dynamic binding, 
make it very attractive for Rapid Application Development, as well as for use as a 
scripting or glue language to connect existing components together.

Python's simple, easy to learn syntax emphasizes readability and therefore reduces 
the cost of program maintenance. Python supports modules and packages, which encourages 
program modularity and code reuse.

Lesson 2: Variables and Data Types
Lesson Link: https://university.edu/python-course/lesson2

In Python, variables are created when you assign a value to them. Unlike many other 
programming languages, Python has no command for declaring a variable. Variables can 
store data of different types, and different types can do different things.

Python has the following built-in data types:
- Text Type: str
- Numeric Types: int, float, complex
- Sequence Types: list, tuple, range
- Boolean Type: bool
"""
            )

            rag = RAGSystem(test_config)
            rag.ai_generator = mock_ai_generator

            # Process the document
            course, chunk_count = rag.add_course_document(str(test_doc))

            # Verify document was processed
            assert course is not None
            assert course.title == "Introduction to Python Programming"
            assert course.instructor == "Dr. Sarah Johnson"
            assert len(course.lessons) == 2
            assert chunk_count > 0

            # Execute a query
            response, sources = rag.query("What are Python's data types?")

            # Verify
            assert response == "Based on the course content, Python is easy to learn."

            # Verify AI generator was called with proper parameters
            mock_ai_generator.generate_response.assert_called_once()
            call_args = mock_ai_generator.generate_response.call_args

            # The query should be properly formatted
            assert "What are Python's data types?" in call_args[1]["query"]

            # Tools should be available
            assert call_args[1]["tools"] is not None
            assert (
                len(call_args[1]["tools"]) >= 1
            )  # At least search tool should be available

            # Tool manager should be passed
            assert call_args[1]["tool_manager"] is not None

    def test_query_prompt_formatting(self, test_config):
        """Test that query prompt is properly formatted"""
        with patch("rag_system.AIGenerator") as mock_ai_generator_class:
            mock_ai_generator = Mock()
            mock_ai_generator.generate_response.return_value = "Test response"
            mock_ai_generator_class.return_value = mock_ai_generator

            rag = RAGSystem(test_config)
            rag.ai_generator = mock_ai_generator
            rag.tool_manager.get_last_sources = Mock(return_value=[])
            rag.tool_manager.reset_sources = Mock()

            # Execute query
            rag.query("What is machine learning?")

            # Verify prompt formatting
            call_args = mock_ai_generator.generate_response.call_args
            prompt = call_args[1]["query"]

            assert "Answer this question about course materials:" in prompt
            assert "What is machine learning?" in prompt
