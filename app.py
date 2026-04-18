from dotenv import load_dotenv
import os

load_dotenv()

if not os.getenv('GROQ_API_KEY'):
    print("Warning: GROQ_API_KEY not found in .env file")

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()