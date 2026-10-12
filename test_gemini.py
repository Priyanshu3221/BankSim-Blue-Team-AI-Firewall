
import os
from dotenv import load_dotenv
from google import genai

load_dotenv(".env")

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not api_key or not api_key.strip():
    print("RESULT: API key is missing")
else:
    try:
        client = genai.Client(api_key=api_key.strip())
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: API_TEST_OK"
        )
        print("RESULT: SUCCESS")
        print("Model:", model)
        print("Response:", response.text)

    except Exception as exc:
        # Print the error type and status, never the request or API key.
        status = getattr(exc, "status_code", None)
        print("RESULT: FAILED")
        print("Error type:", type(exc).__name__)
        print("HTTP status:", status if status else "not provided")
        print("Error:", str(exc).replace(api_key, "[REDACTED]"))
