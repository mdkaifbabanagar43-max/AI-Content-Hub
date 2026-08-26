from datetime import datetime, timezone
from google.cloud import firestore
from core.firestore_client import get_db
from core.models.job import GenerationJob

class GenerationJobRepository:
    def __init__(self):
        self.db = get_db()
        
    def _get_ref(self, user_id: str, project_id: str, blueprint_id: str, job_id: str):
        return self.db.collection("users").document(user_id) \
                      .collection("projects").document(project_id) \
                      .collection("blueprints").document(blueprint_id) \
                      .collection("generation_jobs").document(job_id)

    def _get_user_ref(self, user_id: str):
        return self.db.collection("users").document(user_id)

    def save(self, job: GenerationJob):
        ref = self._get_ref(job.user_id, job.project_id, job.blueprint_id, job.job_id)
        job.updated_at = datetime.now(timezone.utc)
        ref.set(job.model_dump())
        
    def get(self, user_id: str, project_id: str, blueprint_id: str, job_id: str) -> GenerationJob | None:
        doc = self._get_ref(user_id, project_id, blueprint_id, job_id).get()
        if doc.exists:
            return GenerationJob(**doc.to_dict())
        return None

    @firestore.transactional
    def _reserve_credits_transaction(transaction, self, user_ref, ref, job_dict: dict, amount: int) -> bool:
        """Atomic reservation of credits."""
        user_snap = user_ref.get(transaction=transaction)
        if not user_snap.exists:
            raise ValueError("User not found")
            
        current_credits = user_snap.to_dict().get("credits", 0)
        reserved = user_snap.to_dict().get("reserved_credits", 0)
        available = current_credits - reserved
        
        if available < amount:
            raise ValueError(f"Insufficient available credits. Need {amount}, have {available}")
            
        # Create the job as QUEUED
        transaction.set(ref, job_dict)
        
        # Increase reserved credits on user
        transaction.update(user_ref, {
            "reserved_credits": reserved + amount
        })
        return True

    def create_and_reserve(self, job: GenerationJob, amount: int) -> bool:
        user_ref = self._get_user_ref(job.user_id)
        ref = self._get_ref(job.user_id, job.project_id, job.blueprint_id, job.job_id)
        job.reserved_credits = amount
        transaction = self.db.transaction()
        try:
            self._reserve_credits_transaction(transaction, self, user_ref, ref, job.model_dump(), amount)
            return True
        except Exception as e:
            import logging
            logging.error(f"Credit reservation failed: {e}")
            return False

    @firestore.transactional
    def _refund_credits_transaction(transaction, self, user_ref, ref) -> bool:
        """Atomic refund/release of reservation."""
        job_snap = ref.get(transaction=transaction)
        if not job_snap.exists:
            return False
            
        job_data = job_snap.to_dict()
        if job_data.get("status") in ["COMPLETED"]:
            return False # Already paid, can't refund reservation
            
        amount = job_data.get("reserved_credits", 0)
        if amount == 0:
            transaction.update(ref, {"status": "FAILED"})
            return True
            
        user_snap = user_ref.get(transaction=transaction)
        if user_snap.exists:
            reserved = user_snap.to_dict().get("reserved_credits", 0)
            new_reserved = max(0, reserved - amount)
            transaction.update(user_ref, {"reserved_credits": new_reserved})
            
        transaction.update(ref, {
            "status": "FAILED",
            "reserved_credits": 0,
            "failure_reason": "Refunded/Released"
        })
        return True
        
    def release_reservation(self, user_id: str, project_id: str, blueprint_id: str, job_id: str):
        user_ref = self._get_user_ref(user_id)
        ref = self._get_ref(user_id, project_id, blueprint_id, job_id)
        transaction = self.db.transaction()
        try:
            self._refund_credits_transaction(transaction, self, user_ref, ref)
        except Exception:
            pass

    @firestore.transactional
    def try_start_job_transaction(transaction, self, ref) -> bool:
        """Atomic state transition from QUEUED to RUNNING."""
        doc = ref.get(transaction=transaction)
        if not doc.exists:
            return False
            
        data = doc.to_dict()
        if data.get("status") != "QUEUED":
            return False # Duplicate delivery
            
        transaction.update(ref, {
            "status": "RUNNING",
            "started_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
        return True

    def try_start_job(self, user_id: str, project_id: str, blueprint_id: str, job_id: str) -> bool:
        ref = self._get_ref(user_id, project_id, blueprint_id, job_id)
        transaction = self.db.transaction()
        try:
            return self.try_start_job_transaction(transaction, self, ref)
        except Exception as e:
            import logging
            logging.error(f"try_start_job failed with exception: {e}", exc_info=True)
            return False

    @firestore.transactional
    def _commit_credits_transaction(transaction, self, user_ref, ref, user_id: str) -> bool:
        job_snap = ref.get(transaction=transaction)
        if not job_snap.exists:
            return False
            
        job_data = job_snap.to_dict()
        if job_data.get("status") == "COMPLETED":
            return True # Already committed (idempotent)
            
        amount = job_data.get("reserved_credits", 0)
        
        if amount > 0:
            user_snap = user_ref.get(transaction=transaction)
            if user_snap.exists:
                current = user_snap.to_dict().get("credits", 0)
                reserved = user_snap.to_dict().get("reserved_credits", 0)
                
                # Deduct from actual and reserved
                transaction.update(user_ref, {
                    "credits": current - amount,
                    "reserved_credits": max(0, reserved - amount)
                })
                
                # Log to transactions collection
                tx_ref = self.db.collection("transactions").document()
                transaction.set(tx_ref, {
                    "user_id": user_id,
                    "job_id": ref.id,
                    "amount": -amount,
                    "feature": "video_cloner",
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "balance_after": current - amount,
                    "status": "success"
                })
                
        transaction.update(ref, {
            "status": "COMPLETED",
            "completed_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
        return True

    def mark_completed(self, user_id: str, project_id: str, blueprint_id: str, job_id: str):
        user_ref = self._get_user_ref(user_id)
        ref = self._get_ref(user_id, project_id, blueprint_id, job_id)
        transaction = self.db.transaction()
        try:
            self._commit_credits_transaction(transaction, self, user_ref, ref, user_id)
        except Exception as e:
            logging.error(f"Failed to commit credits: {e}")
