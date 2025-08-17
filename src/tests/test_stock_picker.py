"""
Test suite for the stock picker agent functionality.
Tests the stock analysis generation using mocked Azure services.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents import stock_picker
from function_app import (
    tool_properties_stock_picker, 
    tool_properties_stock_picker_json,
    _CHAT_HISTORY_PROPERTY_NAME,
    _USER_QUERY_PROPERTY_NAME
)


class TestStockPickerAgent:
    """Test cases for the stock picker agent implementation."""

    def test_tool_properties_definition(self):
        """Test that stock picker tool properties are properly defined."""
        # Verify tool properties are defined
        assert len(tool_properties_stock_picker) == 2
        
        # Verify property names
        property_names = [prop.propertyName for prop in tool_properties_stock_picker]
        assert _CHAT_HISTORY_PROPERTY_NAME in property_names
        assert _USER_QUERY_PROPERTY_NAME in property_names
        
        # Verify JSON serialization works
        json_data = json.loads(tool_properties_stock_picker_json)
        assert len(json_data) == 2
        assert all('propertyName' in prop for prop in json_data)
        assert all('propertyType' in prop for prop in json_data)
        assert all('description' in prop for prop in json_data)

    @pytest.mark.asyncio
    async def test_generate_stock_analysis_basic(self):
        """Test basic stock analysis generation with mocked Azure services."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'PROJECT_CONNECTION_STRING': 'mock_connection_string',
            'AGENTS_MODEL_DEPLOYMENT_NAME': 'mock_model'
        }):
            # Mock Azure credential
            mock_credential = AsyncMock()
            
            # Mock AI project client and its context manager
            mock_project_client = AsyncMock()
            mock_project_client.__aenter__ = AsyncMock(return_value=mock_project_client)
            mock_project_client.__aexit__ = AsyncMock(return_value=None)
            
            # Mock agent creation and response
            mock_agent = MagicMock()
            mock_agent.id = "test_agent_id"
            mock_agent.name = "StockPickerPro"
            mock_project_client.agents.create_agent = AsyncMock(return_value=mock_agent)
            
            # Mock thread creation
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_project_client.agents.create_thread = AsyncMock(return_value=mock_thread)
            
            # Mock message creation
            mock_project_client.agents.create_message = AsyncMock()
            
            # Mock run creation and execution
            mock_run = MagicMock()
            mock_run.id = "test_run_id"
            mock_run.status = "completed"
            mock_project_client.agents.create_run = AsyncMock(return_value=mock_run)
            mock_project_client.agents.get_run = AsyncMock(return_value=mock_run)
            
            # Mock messages response
            mock_message_content = MagicMock()
            mock_message_content.text.value = "# Stock Analysis Report\n\nMock analysis content"
            mock_message = MagicMock()
            mock_message.content = [mock_message_content]
            mock_messages = MagicMock()
            mock_messages.data = [mock_message]
            mock_project_client.agents.list_messages = AsyncMock(return_value=mock_messages)
            
            with patch('agents.stock_picker.DefaultAzureCredential') as mock_cred_class:
                mock_cred_class.return_value = mock_credential
                mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
                mock_credential.__aexit__ = AsyncMock(return_value=None)
                
                with patch('agents.stock_picker.AIProjectClient.from_connection_string') as mock_client_class:
                    mock_client_class.return_value = mock_project_client
                    
                    with patch('agents.stock_picker.AsyncFunctionTool') as mock_function_tool:
                        mock_tool_instance = MagicMock()
                        mock_tool_instance.definitions = []
                        mock_function_tool.return_value = mock_tool_instance
                        
                        # Test the function
                        result = await stock_picker.generate_stock_analysis(
                            chat_history="Test chat history",
                            user_query="Test stock analysis query"
                        )
                        
                        # Verify the result
                        assert result == "# Stock Analysis Report\n\nMock analysis content"
                        
                        # Verify Azure services were called
                        mock_project_client.agents.create_agent.assert_called_once()
                        mock_project_client.agents.create_thread.assert_called_once()
                        mock_project_client.agents.create_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_stock_analysis_with_tool_calls(self):
        """Test stock analysis generation with agent tool calls."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'PROJECT_CONNECTION_STRING': 'mock_connection_string',
            'AGENTS_MODEL_DEPLOYMENT_NAME': 'mock_model'
        }):
            # Mock Azure credential
            mock_credential = AsyncMock()
            
            # Mock AI project client
            mock_project_client = AsyncMock()
            mock_project_client.__aenter__ = AsyncMock(return_value=mock_project_client)
            mock_project_client.__aexit__ = AsyncMock(return_value=None)
            
            # Mock agent creation
            mock_agent = MagicMock()
            mock_agent.id = "test_agent_id"
            mock_agent.name = "StockPickerPro"
            mock_project_client.agents.create_agent = AsyncMock(return_value=mock_agent)
            
            # Mock thread creation
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_project_client.agents.create_thread = AsyncMock(return_value=mock_thread)
            
            # Mock message creation
            mock_project_client.agents.create_message = AsyncMock()
            
            # Mock run creation with tool calls
            mock_run_action = MagicMock()
            mock_run_action.id = "test_run_id"
            mock_run_action.status = "requires_action"
            
            mock_run_completed = MagicMock()
            mock_run_completed.id = "test_run_id"
            mock_run_completed.status = "completed"
            
            # Mock tool call
            mock_tool_call = MagicMock()
            mock_tool_call.id = "test_tool_call_id"
            mock_tool_call.function.name = "vector_search"
            mock_tool_call.function.arguments = '{"query": "financial analysis"}'
            
            mock_run_action.required_action.submit_tool_outputs.tool_calls = [mock_tool_call]
            
            mock_project_client.agents.create_run = AsyncMock(return_value=mock_run_action)
            mock_project_client.agents.get_run = AsyncMock(side_effect=[mock_run_action, mock_run_completed])
            mock_project_client.agents.submit_tool_outputs_to_run = AsyncMock()
            
            # Mock messages response
            mock_message_content = MagicMock()
            mock_message_content.text.value = "# Stock Analysis Report\n\nAnalysis with tool results"
            mock_message = MagicMock()
            mock_message.content = [mock_message_content]
            mock_messages = MagicMock()
            mock_messages.data = [mock_message]
            mock_project_client.agents.list_messages = AsyncMock(return_value=mock_messages)
            
            with patch('agents.stock_picker.DefaultAzureCredential') as mock_cred_class:
                mock_cred_class.return_value = mock_credential
                mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
                mock_credential.__aexit__ = AsyncMock(return_value=None)
                
                with patch('agents.stock_picker.AIProjectClient.from_connection_string') as mock_client_class:
                    mock_client_class.return_value = mock_project_client
                    
                    with patch('agents.stock_picker.AsyncFunctionTool') as mock_function_tool:
                        mock_tool_instance = AsyncMock()
                        mock_tool_instance.definitions = []
                        mock_tool_instance.execute = AsyncMock(return_value="Mock tool output")
                        mock_function_tool.return_value = mock_tool_instance
                        
                        # Test the function
                        result = await stock_picker.generate_stock_analysis(
                            user_query="Analyze financial data"
                        )
                        
                        # Verify the result
                        assert result == "# Stock Analysis Report\n\nAnalysis with tool results"
                        
                        # Verify tool execution was called
                        mock_tool_instance.execute.assert_called_once_with(mock_tool_call)
                        mock_project_client.agents.submit_tool_outputs_to_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_stock_analysis_error_handling(self):
        """Test error handling in stock analysis generation."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'PROJECT_CONNECTION_STRING': 'mock_connection_string',
            'AGENTS_MODEL_DEPLOYMENT_NAME': 'mock_model'
        }):
            with patch('agents.stock_picker.DefaultAzureCredential') as mock_cred_class:
                # Mock an exception during credential creation
                mock_cred_class.side_effect = Exception("Authentication failed")
                
                # Test that the exception is properly raised
                with pytest.raises(Exception, match="Authentication failed"):
                    await stock_picker.generate_stock_analysis(user_query="Test query")

    def test_system_prompt_content(self):
        """Test that the system prompt contains required financial analysis elements."""
        prompt = stock_picker._STOCK_PICKER_SYSTEM_PROMPT
        
        # Verify key financial analysis components are mentioned
        assert "StockPickerPro" in prompt
        assert "financial analysis" in prompt
        assert "investment recommendations" in prompt
        assert "vector_search" in prompt
        assert "risk" in prompt.lower()
        assert "portfolio" in prompt.lower()
        assert "investment strategy" in prompt.lower()
        
        # Verify it follows the established pattern
        assert "SINGLE vector search" in prompt
        assert "Markdown format" in prompt
        assert "Return only the final Markdown document" in prompt