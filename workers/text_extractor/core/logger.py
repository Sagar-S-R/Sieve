import logging

# Simple logging setup - no over-engineering
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Export logger object for imports
logger = logging.getLogger(__name__)
