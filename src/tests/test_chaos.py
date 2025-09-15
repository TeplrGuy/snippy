"""Unit tests for chaos engineering functionality."""

import asyncio
import os
from unittest.mock import patch

import pytest

from chaos import ChaosException, get_chaos_config, inject_chaos_if_enabled


class TestChaos:
    """Test cases for the chaos engineering module."""
    
    @pytest.mark.asyncio
    async def test_force_error(self):
        """Test that inject_chaos_if_enabled raises ChaosException when forced."""
        with patch.dict(os.environ, {
            'CHAOS_ENABLED': 'true',
            'CHAOS_INJECT_ERROR_RATE': '1.0',  # Force error
            'CHAOS_DELAY_SECONDS_MAX': '0'     # No delay
        }):
            with pytest.raises(ChaosException) as exc_info:
                await inject_chaos_if_enabled()
            
            assert "Chaos engineering: simulated service failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_force_delay_no_error(self, monkeypatch):
        """Test that inject_chaos_if_enabled does not raise exception with no error rate."""
        # Mock asyncio.sleep to avoid real delays
        sleep_called = []
        
        async def mock_sleep(delay):
            sleep_called.append(delay)
        
        monkeypatch.setattr(asyncio, 'sleep', mock_sleep)
        
        with patch.dict(os.environ, {
            'CHAOS_ENABLED': 'true',
            'CHAOS_INJECT_ERROR_RATE': '0.0',  # No errors
            'CHAOS_DELAY_SECONDS_MAX': '0'     # No delay
        }):
            # Should not raise exception
            await inject_chaos_if_enabled()
        
        # Should not have called sleep with max delay of 0
        assert len(sleep_called) == 0

    @pytest.mark.asyncio
    async def test_chaos_disabled(self):
        """Test that chaos injection is skipped when disabled."""
        with patch.dict(os.environ, {
            'CHAOS_ENABLED': 'false',
            'CHAOS_INJECT_ERROR_RATE': '1.0',
            'CHAOS_DELAY_SECONDS_MAX': '10'
        }):
            # Should return immediately without error or delay
            await inject_chaos_if_enabled()

    def test_get_chaos_config_defaults(self):
        """Test chaos configuration with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_chaos_config()
            
            assert config["CHAOS_ENABLED"] is False
            assert config["CHAOS_INJECT_ERROR_RATE"] == 0.1
            assert config["CHAOS_DELAY_SECONDS_MAX"] == 5

    def test_get_chaos_config_custom(self):
        """Test chaos configuration with custom values."""
        with patch.dict(os.environ, {
            'CHAOS_ENABLED': 'true',
            'CHAOS_INJECT_ERROR_RATE': '0.25',
            'CHAOS_DELAY_SECONDS_MAX': '3'
        }):
            config = get_chaos_config()
            
            assert config["CHAOS_ENABLED"] is True
            assert config["CHAOS_INJECT_ERROR_RATE"] == 0.25
            assert config["CHAOS_DELAY_SECONDS_MAX"] == 3

    @pytest.mark.asyncio
    async def test_delay_injection(self, monkeypatch):
        """Test that delays are injected when configured."""
        sleep_called = []
        
        async def mock_sleep(delay):
            sleep_called.append(delay)
        
        monkeypatch.setattr(asyncio, 'sleep', mock_sleep)
        
        with patch.dict(os.environ, {
            'CHAOS_ENABLED': 'true',
            'CHAOS_INJECT_ERROR_RATE': '0.0',  # No errors
            'CHAOS_DELAY_SECONDS_MAX': '2'     # Max 2 second delay
        }):
            await inject_chaos_if_enabled()
        
        # Should have called sleep once with a delay between 0 and 2
        assert len(sleep_called) == 1
        assert 0 <= sleep_called[0] <= 2