import sys
import os

# Adapt import path for different contexts (Run as script vs Module)
# Adapt import path
try:
    from firebase_utils import db, firestore
    from models import InsufficientFundsError, FeatureLockedError
except ImportError:
    # If running as script or sub-module where root is not in path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from firebase_utils import db, firestore
    from models import InsufficientFundsError, FeatureLockedError

def check_feature_access(user_plan: str, feature_name: str):
    """
    Verifies if the user's plan allows access to the specific feature.
    Raises FeatureLockedError if access is denied.
    """
    # Simple Logic: Starter plan has manual restrictions.
    # In a real app, config.py would have a FEATURES_BY_PLAN dict.
    # For now, we hardcode based on the implementation plan requirements.
    
    # Example Restriction: 'lipsync' is NOT for Starter.
    if feature_name == 'lipsync' and user_plan == 'starter':
        raise FeatureLockedError(f"Feature '{feature_name}' is locked for {user_plan} plan. Please upgrade.")
        
    return True

@firestore.transactional
def deduct_credits_transactional(transaction, user_ref, amount: int, feature_used: str, user_id: str):
    """
    Transactional logic to be used with db.transaction().
    """
    snapshot = user_ref.get(transaction=transaction)
    
    if not snapshot.exists:
        raise ValueError("User not found")
        
    user_data = snapshot.to_dict()
    current_credits = user_data.get('credits', 0)
    
    if current_credits < amount:
        raise InsufficientFundsError(f"Insufficient funds: Has {current_credits}, needs {amount}")
        
    # 1. Deduct Credits
    transaction.update(user_ref, {
        "credits": current_credits - amount
    })
    
    # 2. Log Transaction (Create new doc)
    # Note: We can't use Pydantic directly in Firestore set easily without dict conversion
    new_tx_ref = db.collection("transactions").document()
    
    tx_record = {
        "id": new_tx_ref.id,
        "user_id": user_id,
        "amount": -amount, # Negative for spend
        "feature_used": feature_used,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "balance_after": current_credits - amount,
        "status": "success"
    }
    
    transaction.set(new_tx_ref, tx_record)
    
    return current_credits - amount


def complete_job_and_deduct(user_id: str, job_id: str, amount: int, feature_used: str):
    """
    Transactional:
    1. Checks if job is already paid (idempotency).
    2. Checks user balance.
    3. Deducts credits.
    4. Marks job as 'paid' & 'completed'.
    """
    transaction = db.transaction()
    user_ref = db.collection("users").document(user_id)
    job_ref = user_ref.collection("jobs").document(job_id)

    try:
        _complete_job_transaction(transaction, user_ref, job_ref, amount, feature_used, user_id)
        print(f"✅ Job {job_id} Completed & Paid (-{amount} credits)")
        return True
    except Exception as e:
        print(f"❌ Job Completion Transaction Failed: {e}")
        # Identify if it was "Already Paid" (not an error, just idempotent success)
        if "Already paid" in str(e):
            print("Job was already paid. returning Success.")
            return True
        raise e

@firestore.transactional
def _complete_job_transaction(transaction, user_ref, job_ref, amount: int, feature_used: str, user_id: str):
    user_snapshot = user_ref.get(transaction=transaction)
    job_snapshot = job_ref.get(transaction=transaction)

    # 1. Validate User
    if not user_snapshot.exists:
        raise ValueError("User not found")
    
    # 2. Validate Job
    if not job_snapshot.exists:
        # If job doc doesn't exist, we assume it's a "Ghost Job" (shouldn't happen if created properly)
        # But for safety, we can create it or fail. Failsafe: Create if missing? 
        # No, strict mode: Job must exist (created at start of endpoint).
        raise ValueError(f"Job {job_ref.id} not found/init.")

    job_data = job_snapshot.to_dict()
    
    # 3. Idempotency Check
    if job_data.get('credits_deducted', False):
        raise ValueError("Already paid")

    current_credits = user_snapshot.get('credits') or 0
    if current_credits < amount:
        # Mark job as failed_payment? Or just fail tx?
        transaction.update(job_ref, {"status": "failed_payment"})
        raise InsufficientFundsError(f"Insufficient funds: Has {current_credits}, needs {amount}")

    # 4. Execute Deduction
    new_balance = current_credits - amount
    transaction.update(user_ref, {"credits": new_balance})

    # 5. Execute Job Completion
    transaction.update(job_ref, {
        "status": "completed",
        "credits_deducted": True,
        "cost": amount,
        "completed_at": firestore.SERVER_TIMESTAMP
    })

    # 6. Log Transaction (Ledger)
    new_tx_ref = db.collection("transactions").document()
    transaction.set(new_tx_ref, {
        "user_id": user_id,
        "job_id": job_ref.id,
        "amount": -amount,
        "feature": feature_used,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "balance_after": new_balance,
        "status": "success"
    })

