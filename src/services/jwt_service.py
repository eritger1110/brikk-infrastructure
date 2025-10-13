# -*- coding: utf-8 -*-
class JWTService:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def create_token(self, identity: str, claims: dict) -> str:
        return "dummy_token"
