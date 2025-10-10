from .db import db

def get_db():
    yield db.session
