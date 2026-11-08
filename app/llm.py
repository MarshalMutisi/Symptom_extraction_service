import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

client = Groq(api_key=os.environ["GROQ_API_KEY"])
