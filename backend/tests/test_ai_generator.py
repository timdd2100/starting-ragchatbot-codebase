from unittest.mock import MagicMock, Mock, patch

import anthropic
import pytest

from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager


class TestAIGenerator:
    """Test AIGenerator functionality including tool calling"""

    def test_init(self):
        """Test AIGenerator initialization"""
        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        assert generator.model == "claude-3-sonnet-20240229"
        assert generator.base_params["model"] == "claude-3-sonnet-20240229"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_simple(self, mock_anthropic_class):
        """Test simple response generation without tools"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="This is a simple response.")]
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Execute
        result = generator.generate_response("What is Python?")

        # Verify
        assert result == "This is a simple response."
        mock_client.messages.create.assert_called_once()

        # Check call arguments
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["messages"][0]["content"] == "What is Python?"
        assert call_args[1]["model"] == "claude-3-sonnet-20240229"

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_conversation_history(self, mock_anthropic_class):
        """Test response generation with conversation history"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response with context.")]
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Execute
        result = generator.generate_response(
            query="Tell me more",
            conversation_history="User: What is Python?\nAssistant: Python is a programming language.",
        )

        # Verify
        assert result == "Response with context."

        # Check that conversation history is included in system prompt
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation:" in system_content
        assert "What is Python?" in system_content

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_tool_calling(self, mock_anthropic_class):
        """Test response generation with tool calling workflow"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.id = "tool_123"
        mock_tool_content.input = {"query": "Python basics"}

        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [mock_tool_content]

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [
            Mock(text="Based on the search results, Python is a programming language.")
        ]

        # Configure client to return tool response first, then final response
        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        mock_anthropic_class.return_value = mock_client
        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "Python is a high-level programming language."
        )

        # Mock tools
        mock_tools = [
            {"name": "search_course_content", "description": "Search course content"}
        ]

        # Execute
        result = generator.generate_response(
            query="What is Python?", tools=mock_tools, tool_manager=mock_tool_manager
        )

        # Verify
        assert (
            result == "Based on the search results, Python is a programming language."
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="Python basics"
        )

        # Verify two API calls were made (tool use + final response)
        assert mock_client.messages.create.call_count == 2

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_tool_call_api_error(self, mock_anthropic_class):
        """Test handling of API errors during tool calling"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock API error
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")

        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Execute and verify exception is raised
        with pytest.raises(Exception):
            generator.generate_response("What is Python?")

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_tool_execution_error(self, mock_anthropic_class):
        """Test handling of tool execution errors"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.id = "tool_123"
        mock_tool_content.input = {"query": "Python basics"}

        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [mock_tool_content]

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [
            Mock(text="I couldn't find relevant information.")
        ]

        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        mock_anthropic_class.return_value = mock_client
        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Mock tool manager that returns error
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "Tool execution failed: Database connection error"
        )

        mock_tools = [
            {"name": "search_course_content", "description": "Search course content"}
        ]

        # Execute
        result = generator.generate_response(
            query="What is Python?", tools=mock_tools, tool_manager=mock_tool_manager
        )

        # Verify
        assert result == "I couldn't find relevant information."

        # Verify tool was executed and error was passed through
        mock_tool_manager.execute_tool.assert_called_once()

    @patch("ai_generator.anthropic.Anthropic")
    def test_handle_tool_execution_multiple_tools(self, mock_anthropic_class):
        """Test handling multiple tool calls in a single response"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock multiple tool use content blocks
        mock_tool_content1 = Mock()
        mock_tool_content1.type = "tool_use"
        mock_tool_content1.name = "search_course_content"
        mock_tool_content1.id = "tool_123"
        mock_tool_content1.input = {"query": "Python"}

        mock_tool_content2 = Mock()
        mock_tool_content2.type = "tool_use"
        mock_tool_content2.name = "search_course_content"
        mock_tool_content2.id = "tool_456"
        mock_tool_content2.input = {"query": "variables"}

        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [mock_tool_content1, mock_tool_content2]

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [
            Mock(text="Combined results from both searches.")
        ]

        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        mock_anthropic_class.return_value = mock_client
        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Python result",
            "Variables result",
        ]

        mock_tools = [
            {"name": "search_course_content", "description": "Search course content"}
        ]

        # Execute
        result = generator.generate_response(
            query="What are Python variables?",
            tools=mock_tools,
            tool_manager=mock_tool_manager,
        )

        # Verify
        assert result == "Combined results from both searches."
        assert mock_tool_manager.execute_tool.call_count == 2

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_choice_auto_included(self, mock_anthropic_class):
        """Test that tool_choice is set to auto when tools are provided"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response with tools available.")]
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        mock_tools = [
            {"name": "search_course_content", "description": "Search course content"}
        ]

        # Execute
        generator.generate_response(query="What is Python?", tools=mock_tools)

        # Verify tool_choice was included
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["tools"] == mock_tools
        assert call_args[1]["tool_choice"] == {"type": "auto"}

    def test_system_prompt_content(self):
        """Test that system prompt contains expected content"""
        assert "educational content" in AIGenerator.SYSTEM_PROMPT
        assert "search_course_content" in AIGenerator.SYSTEM_PROMPT
        assert "get_course_outline" in AIGenerator.SYSTEM_PROMPT
        assert "Tool Usage Guidelines" in AIGenerator.SYSTEM_PROMPT
        assert "Response Protocol" in AIGenerator.SYSTEM_PROMPT

    @patch("ai_generator.anthropic.Anthropic")
    def test_no_tools_no_tool_choice(self, mock_anthropic_class):
        """Test that tool_choice is not included when no tools are provided"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response without tools.")]
        mock_client.messages.create.return_value = mock_response

        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Execute
        generator.generate_response(query="What is Python?")

        # Verify tool_choice was not included
        call_args = mock_client.messages.create.call_args
        assert "tools" not in call_args[1]
        assert "tool_choice" not in call_args[1]

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_without_manager_no_execution(self, mock_anthropic_class):
        """Test that tools aren't executed if no tool_manager is provided"""
        # Setup
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.id = "tool_123"
        mock_tool_content.input = {"query": "Python basics"}

        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [mock_tool_content]

        mock_client.messages.create.return_value = mock_tool_response

        mock_anthropic_class.return_value = mock_client
        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        mock_tools = [
            {"name": "search_course_content", "description": "Search course content"}
        ]

        # Execute without tool_manager
        result = generator.generate_response(
            query="What is Python?",
            tools=mock_tools,
            tool_manager=None,  # No tool manager provided
        )

        # Verify - should return the tool_use content directly since can't execute
        # This is a bit of an edge case but we should handle it gracefully
        assert result is not None
        # Only one API call should have been made
        assert mock_client.messages.create.call_count == 1


class TestAIGeneratorIntegration:
    """Integration tests for AIGenerator with real tool manager"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_integration_with_real_tool_manager(self, mock_anthropic_class):
        """Test AIGenerator with a real ToolManager and mocked CourseSearchTool"""
        # Setup anthropic mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_content = Mock()
        mock_tool_content.type = "tool_use"
        mock_tool_content.name = "search_course_content"
        mock_tool_content.id = "tool_123"
        mock_tool_content.input = {"query": "Python programming"}

        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [mock_tool_content]

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [
            Mock(text="Python is a versatile programming language.")
        ]

        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        # Setup real tool manager with mocked vector store
        mock_vector_store = Mock()
        from .conftest import create_search_results

        mock_vector_store.search.return_value = create_search_results(
            documents=["Python is easy to learn and use."],
            course_title="Python Fundamentals",
        )

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)

        generator = AIGenerator("test-api-key", "claude-3-sonnet-20240229")

        # Execute
        result = generator.generate_response(
            query="What is Python?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Verify
        assert result == "Python is a versatile programming language."

        # Verify tool was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="Python programming", course_name=None, lesson_number=None
        )
