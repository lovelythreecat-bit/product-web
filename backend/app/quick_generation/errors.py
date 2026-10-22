from fastapi import HTTPException


class QuickGenerationError(HTTPException):
    """Only static, caller-safe workflow guidance is accepted by this service."""
