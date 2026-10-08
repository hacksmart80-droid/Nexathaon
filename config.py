import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# File upload configuration
MAX_CONTENT_LENGTH = 15 * 1024 * 1024  # 15 MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Directory paths
DATA_DIR = os.path.join(BASE_DIR, 'data')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
TEMP_CASES_DIR = os.path.join(TEMP_DIR, 'cases')
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, 'sample_data')

# Data files
SCHOLARSHIPS_FILE = os.path.join(DATA_DIR, 'scholarships.json')

# Session / case settings
CASE_EXPIRY_SECONDS = 7200  # 2 hours

# Server settings
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5000))
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')
