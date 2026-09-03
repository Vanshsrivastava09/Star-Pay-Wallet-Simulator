from app.main import app
from mangum import Mangum

# Vercel serverless handler for FastAPI
handler = Mangum(app)


