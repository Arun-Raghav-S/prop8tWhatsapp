"""
Structured logging utility for WhatsApp Agent System
"""

import logging
import structlog
import os
from typing import Any, Dict


def setup_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Setup structured logger with Google Cloud Logging compatibility
    """
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=logging.INFO if os.getenv("DEBUG") != "1" else logging.DEBUG,
    )
    
    # Create structured logger
    logger = structlog.get_logger(name)
    
    return logger


def log_agent_interaction(
    logger: structlog.stdlib.BoundLogger,
    user_id: str,
    agent_name: str,
    input_message: str,
    output_message: str,
    processing_time_ms: float,
    metadata: Dict[str, Any] = None
) -> None:
    """
    Log agent interactions with structured metadata
    """
    logger.info(
        "Agent interaction completed",
        user_id=user_id,
        agent_name=agent_name,
        input_length=len(input_message),
        output_length=len(output_message),
        processing_time_ms=processing_time_ms,
        metadata=metadata or {}
    )


def log_error_with_context(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    context: Dict[str, Any],
    operation: str
) -> None:
    """
    Log errors with rich context information
    """
    logger.error(
        f"Operation failed: {operation}",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context
    ) 