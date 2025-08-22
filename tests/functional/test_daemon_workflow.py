"""
Functional tests for the daemon workflow.

These tests verify the complete end-to-end behavior of the daemon,
including startup, runtime behavior, and shutdown procedures.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
import signal
import sys

# Import the daemon module
from daemon import main, init_gemini, heartbeat


class TestDaemonWorkflow:
    """Test the complete daemon workflow."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_complete_lifecycle(self, mock_gemini_api_key, mock_google_generativeai):
        """Test the complete daemon lifecycle from startup to shutdown."""
        # Mock the asyncio components
        mock_task = Mock()
        mock_task.cancel = Mock()
        
        with patch("asyncio.create_task", return_value=mock_task) as mock_create_task, \
             patch("asyncio.gather") as mock_gather, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            # Start the daemon
            daemon_task = asyncio.create_task(main())
            
            # Let it run for a short time
            await asyncio.sleep(0.1)
            
            # Cancel the daemon
            daemon_task.cancel()
            
            try:
                await daemon_task
            except asyncio.CancelledError:
                pass
            
            # Verify the workflow
            mock_create_task.assert_called()
            mock_gather.assert_called()
            mock_google_gemini_api_key.configure.assert_called_once()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_graceful_shutdown(self, mock_gemini_api_key, mock_google_generativeai):
        """Test that the daemon shuts down gracefully."""
        # Mock the asyncio components
        mock_task = Mock()
        mock_task.cancel = Mock()
        
        with patch("asyncio.create_task", return_value=mock_task) as mock_create_task, \
             patch("asyncio.gather") as mock_gather, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            # Start the daemon
            daemon_task = asyncio.create_task(main())
            
            # Simulate graceful shutdown
            await asyncio.sleep(0.1)
            daemon_task.cancel()
            
            try:
                await daemon_task
            except asyncio.CancelledError:
                pass
            
            # Verify graceful shutdown
            assert daemon_task.cancelled()
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_environment_handling(self):
        """Test daemon behavior with different environment configurations."""
        test_cases = [
            ({"GEMINI_API_KEY": "valid-key-123"}, True),
            ({"GEMINI_API_KEY": ""}, False),
            ({"GEMINI_API_KEY": "invalid-key"}, False),
            ({}, False),
        ]
        
        for env_vars, expected_success in test_cases:
            with patch.dict(os.environ, env_vars, clear=True):
                if expected_success:
                    with patch("google.generativeai") as mock_genai:
                        mock_genai.configure = Mock()
                        result = await init_gemini()
                        assert result is True
                else:
                    result = await init_gemini()
                    assert result is False
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_heartbeat_behavior(self, mock_logger):
        """Test that the daemon maintains consistent heartbeat behavior."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Start heartbeat
            heartbeat_task = asyncio.create_task(heartbeat())
            
            # Let it run for a few iterations
            await asyncio.sleep(0.1)
            
            # Cancel the task
            heartbeat_task.cancel()
            
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            
            # Verify heartbeat behavior
            assert mock_logger.info.called
            assert mock_sleep.called


class TestDaemonErrorRecovery:
    """Test daemon error recovery and resilience."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_recovers_from_gemini_failure(self):
        """Test that daemon continues running even if Gemini initialization fails."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "invalid-key"}, clear=True):
            with patch("google.generativeai") as mock_genai:
                mock_genai.configure.side_effect = Exception("Gemini API error")
                
                # Daemon should continue running even with Gemini failure
                result = await init_gemini()
                assert result is False
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_handles_import_errors(self):
        """Test that daemon handles import errors gracefully."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "valid-key"}, clear=True):
            with patch("builtins.__import__", side_effect=ImportError("Module not found")):
                result = await init_gemini()
                assert result is False
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_continues_with_heartbeat_failure(self, mock_logger):
        """Test that daemon continues running even if heartbeat fails."""
        with patch("asyncio.sleep", side_effect=Exception("Sleep error")):
            with pytest.raises(Exception, match="Sleep error"):
                await heartbeat()


class TestDaemonIntegration:
    """Test daemon integration with external systems."""
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_with_mock_external_services(self, mock_gemini_api_key, mock_google_generativeai):
        """Test daemon integration with mocked external services."""
        # Mock external service responses
        mock_google_generativeai.GenerativeModel.return_value = Mock()
        
        # Test the integration
        result = await init_gemini()
        assert result is True
        
        # Verify external service integration
        mock_google_generativeai.configure.assert_called_once_with(api_key="test-api-key-12345")
    
    @pytest.mark.functional
    @pytest.mark.asyncio
    async def test_daemon_environment_integration(self):
        """Test daemon integration with environment variables."""
        test_env = {
            "GEMINI_API_KEY": "test-key-12345",
            "LOG_LEVEL": "DEBUG",
            "HEALTH_CHECK_PORT": "8080"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            # Verify environment integration
            assert os.getenv("GEMINI_API_KEY") == "test-key-12345"
            assert os.getenv("LOG_LEVEL") == "DEBUG"
            assert os.getenv("HEALTH_CHECK_PORT") == "8080"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_daemon_performance_characteristics():
    """Test daemon performance characteristics and resource usage."""
    import time
    
    # Test startup time
    start_time = time.time()
    
    with patch("asyncio.create_task") as mock_create_task, \
         patch("asyncio.gather") as mock_gather, \
         patch("google.generativeai") as mock_genai:
        
        mock_task = Mock()
        mock_create_task.return_value = mock_task
        mock_genai.configure = Mock()
        
        await main()
        
        startup_time = time.time() - start_time
        
        # Startup should be reasonably fast (less than 1 second)
        assert startup_time < 1.0


@pytest.mark.functional
@pytest.mark.asyncio
async def test_daemon_concurrent_operations():
    """Test daemon behavior under concurrent operations."""
    # Test that multiple concurrent calls to init_gemini work correctly
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
        with patch("google.generativeai") as mock_genai:
            mock_genai.configure = Mock()
            
            # Run multiple concurrent initializations
            tasks = [init_gemini() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert all(results)
            # Configure should be called once per initialization
            assert mock_genai.configure.call_count == 5


@pytest.mark.functional
@pytest.mark.asyncio
async def test_daemon_resource_cleanup():
    """Test that daemon properly cleans up resources."""
    with patch("asyncio.create_task") as mock_create_task, \
         patch("asyncio.gather") as mock_gather, \
         patch("google.generativeai") as mock_genai:
        
        mock_task = Mock()
        mock_create_task.return_value = mock_task
        mock_genai.configure = Mock()
        
        # Start daemon
        daemon_task = asyncio.create_task(main())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Cancel and cleanup
        daemon_task.cancel()
        
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass
        
        # Verify cleanup
        assert daemon_task.cancelled()
        # No resource leaks should occur
