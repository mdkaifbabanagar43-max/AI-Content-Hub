import sys
import os
import time

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

try:
    from services.credit_service import deduct_credits_atomic, check_feature_access
    from models import InsufficientFundsError, FeatureLockedError
    from firebase_utils import db
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Ensure you are running this from the root of the repo or backend folder.")
    sys.exit(1)

def run_audit():
    print("🕵️ STARING BANK-GRADE BILLING AUDIT")
    print("===================================")
    
    # SETUP
    starter_id = "audit_starter_user"
    broke_id = "audit_broke_user"
    rich_id = "audit_rich_user"
    
    # Clean previous test data
    print("\n🧹 Cleaning Test Data...")
    db.collection("users").document(starter_id).set({"plan": "starter", "credits": 50})
    db.collection("users").document(broke_id).set({"plan": "starter", "credits": 5})
    db.collection("users").document(rich_id).set({"plan": "creator", "credits": 100})
    print("✅ Test Users Reset.")
    
    # CHECK A: Feature Gate
    print("\n🧪 Check A: The Feature Gate (LipSync Locked for Starter)")
    try:
        check_feature_access('starter', 'lipsync')
        print("❌ FAILED: Starter user accessed LipSync!")
    except FeatureLockedError:
        print("✅ PASSED: System blocked Starter user from LipSync.")
    except Exception as e:
        print(f"❌ ERROR: Unexpected exception: {e}")

    # CHECK B: Bankruptcy Check
    print("\n🧪 Check B: The Bankruptcy Check (5 Credits vs 10 Cost)")
    try:
        deduct_credits_atomic(broke_id, 10, "test_bankruptcy")
        print("❌ FAILED: Broke user spent money they don't have!")
    except InsufficientFundsError:
         print("✅ PASSED: Transaction rejected due to insufficient funds.")
    except Exception as e:
        print(f"❌ ERROR: Unexpected exception: {e}")
        
    # CHECK C: Deduction Integrity
    print("\n🧪 Check C: The Deduction Integrity (100 - 20 = 80)")
    try:
        deduct_credits_atomic(rich_id, 20, "test_deduction")
        
        # Verify DB State
        doc = db.collection("users").document(rich_id).get()
        new_bal = doc.to_dict().get('credits')
        
        if new_bal == 80:
             print(f"✅ PASSED: Balance is exactly 80. (Verified in DB)")
        else:
             print(f"❌ FAILED: Balance is {new_bal}, expected 80.")
             
    except Exception as e:
        print(f"❌ ERROR: Deduction failed: {e}")

    # CHECK D: Plan Sync & Webhook Simulation
    print("\n🧪 Check D: The Plan Sync (Upgrade to Agency)")
    try:
        # Simulate Webhook Update
        db.collection("users").document(starter_id).update({
            "plan": "agency",
            "credits": 10000
        })
        
        # Verify
        doc = db.collection("users").document(starter_id).get()
        data = doc.to_dict()
        if data['plan'] == 'agency' and data['credits'] == 10000:
             print("✅ PASSED: User successfully upgraded to Agency.")
        else:
             print(f"❌ FAILED: Upgrade failed. Plan: {data.get('plan')}")
             
    except Exception as e:
        print(f"❌ ERROR: Sync failed: {e}")

    print("\n===================================")
    print("🎉 AUDIT COMPLETE.")

if __name__ == "__main__":
    run_audit()
