from pydantic import BaseModel
from datetime import datetime

class Transaction(BaseModel):
    id: str
    user_id: str
    amount: int  # Negative for spend, positive for purchase/refund
    feature_used: str
    timestamp: datetime = datetime.now()
    status: str = "success"

class FeatureLockedError(Exception):
    """Raised when a user tries to access a feature not in their plan."""
    pass

class InsufficientFundsError(Exception):
    """Raised when a user does not have enough credits."""
    pass
