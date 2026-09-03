import sys
from pathlib import Path

# Add api directory to Python path so app module can be found
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
from mangum import Mangum

# Vercel serverless handler for FastAPI
handler = Mangum(app)


