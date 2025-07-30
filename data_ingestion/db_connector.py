from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()
DB_URI = os.getenv("DB_URI")

def get_engine():
    return create_engine(DB_URI)
