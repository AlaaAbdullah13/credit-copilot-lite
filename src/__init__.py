"""Application package configuration."""

from dotenv import load_dotenv

# Load project-local defaults without replacing values supplied by the runtime.
load_dotenv(override=False)
