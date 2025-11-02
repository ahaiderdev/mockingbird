"""Main entry point for the synthetic metrics generator."""
import argparse
import logging
import sys
import threading
import signal
import time

from src.config import load_config
from src.engine import GeneratorEngine, run_engine_thread
from src.control_api import ControlAPI


def setup_logging(log_level: str, log_format: str):
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    if log_format == "json":
        # For JSON logging, you'd use a library like python-json-logger
        # For now, use structured text format
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Reduce noise from some libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Synthetic Metrics Generator - Generate metrics for testing"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to configuration YAML file"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Setup logging
    setup_logging(config.global_.log_level, config.global_.log_format)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Synthetic Metrics Generator")
    logger.info("=" * 60)
    logger.info(f"Configuration loaded from: {args.config}")
    logger.info(f"Tick interval: {config.global_.tick_interval_s}s")
    logger.info(f"Global seed: {config.global_.seed}")
    logger.info(f"Metrics configured: {len(config.metrics)}")
    
    # Initialize engine (without control_api reference initially)
    try:
        engine = GeneratorEngine(config, control_api=None)
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}", exc_info=True)
        sys.exit(1)
    
    # Initialize control API with engine reference
    control_api = ControlAPI(engine)
    
    # Connect control_api back to engine for spike functionality
    engine.control_api = control_api
    logger.info("Control API connected to engine for spike functionality")
    
    # Start engine in separate thread
    engine_thread = threading.Thread(
        target=run_engine_thread,
        args=(engine,),
        daemon=True
    )
    engine_thread.start()
    logger.info("Generator engine started")
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        engine.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run control API (blocking)
    logger.info(f"Starting control API on port {config.global_.control_api_port}")
    try:
        control_api.run(
            host="0.0.0.0",
            port=config.global_.control_api_port
        )
    except Exception as e:
        logger.error(f"Control API error: {e}", exc_info=True)
        engine.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()

