# Module for chaos engineering functionality:
# - ChaosException for simulated failures
# - Configuration reading from environment variables
# - Async chaos injection with probability-based errors and delays
# - Structured logging for chaos events

import asyncio
import logging
import os
import random
from typing import Dict, Union

# Configure logging for this module
logger = logging.getLogger(__name__)


class ChaosException(Exception):
    """Exception raised during chaos injection to simulate service failures."""
    pass


def get_chaos_config() -> Dict[str, Union[bool, float, int]]:
    """Get chaos configuration from environment variables, read dynamically each call."""
    return {
        "CHAOS_ENABLED": os.environ.get("CHAOS_ENABLED", "false").lower() in ("true", "1", "yes"),
        "CHAOS_INJECT_ERROR_RATE": float(os.environ.get("CHAOS_INJECT_ERROR_RATE", "0.1")),
        "CHAOS_DELAY_SECONDS_MAX": int(os.environ.get("CHAOS_DELAY_SECONDS_MAX", "5"))
    }


async def inject_chaos_if_enabled() -> None:
    """Inject chaos if enabled: random errors and/or delays based on configuration."""
    config = get_chaos_config()
    
    # Early return if chaos is disabled
    if not config["CHAOS_ENABLED"]:
        return
    
    # Generate random probability for this invocation
    probability = random.random()
    error_rate = config["CHAOS_INJECT_ERROR_RATE"]
    max_delay = config["CHAOS_DELAY_SECONDS_MAX"]
    
    # Check if we should inject an error
    if probability < error_rate:
        logger.warning(
            "CHAOS[error]: Injecting failure - probability=%.3f < error_rate=%.3f, "
            "env_values={CHAOS_ENABLED=%s, CHAOS_INJECT_ERROR_RATE=%.3f, CHAOS_DELAY_SECONDS_MAX=%d}",
            probability, error_rate, config["CHAOS_ENABLED"], error_rate, max_delay,
            extra={
                "event_type": "error",
                "probability": probability,
                "error_rate": error_rate,
                "chaos_config": config
            }
        )
        raise ChaosException("Chaos engineering: simulated service failure")
    
    # If no error and delay is enabled, inject random delay
    if max_delay > 0:
        delay_seconds = random.uniform(0, max_delay)
        logger.warning(
            "CHAOS[delay]: Injecting delay - delay_seconds=%.3f, probability=%.3f >= error_rate=%.3f, "
            "env_values={CHAOS_ENABLED=%s, CHAOS_INJECT_ERROR_RATE=%.3f, CHAOS_DELAY_SECONDS_MAX=%d}",
            delay_seconds, probability, error_rate, config["CHAOS_ENABLED"], error_rate, max_delay,
            extra={
                "event_type": "delay",
                "delay_seconds": delay_seconds,
                "probability": probability,
                "error_rate": error_rate,
                "chaos_config": config
            }
        )
        await asyncio.sleep(delay_seconds)