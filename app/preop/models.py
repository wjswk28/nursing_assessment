from app import db
from datetime import datetime
import uuid


def generate_token():
    return uuid.uuid4().hex
