import subprocess
import time
import json
import sys

def test_endpoint():
    print("Starting uvicorn server on port 8055...")
    # Stream stdout and stderr directly to our console so we can see what's happening
    proc = subprocess.Popen(
        ["/Users/likithnaidu/Desktop/forms-project/backend/venv/bin/uvicorn", "main:app", "--port", "8055"],
        cwd="/Users/likithnaidu/Desktop/forms-project/backend",
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    print("Waiting for server to initialize...")
    time.sleep(15)
    
    try:
        print("\nTesting valid receipt image (receipt_seed_1.jpg)...")
        res_receipt = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                "-F", "file=@/Users/likithnaidu/Desktop/forms-project/dataset/test/receipt/receipt_seed_1.jpg",
                "http://127.0.0.1:8055/api/receipt/predict"
            ],
            capture_output=True,
            text=True
        )
        print("Receipt Response:")
        try:
            parsed = json.loads(res_receipt.stdout)
            print(json.dumps(parsed, indent=2))
        except Exception:
            print("Raw output:", repr(res_receipt.stdout))
            print("Curl stderr:", res_receipt.stderr)
        
        print("\nTesting non-receipt image (synthetic_doc_0.png)...")
        res_non_receipt = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                "-F", "file=@/Users/likithnaidu/Desktop/forms-project/dataset/test/not_receipt/synthetic_doc_0.png",
                "http://127.0.0.1:8055/api/receipt/predict"
            ],
            capture_output=True,
            text=True
        )
        print("Non-receipt Response:")
        try:
            parsed = json.loads(res_non_receipt.stdout)
            print(json.dumps(parsed, indent=2))
        except Exception:
            print("Raw output:", repr(res_non_receipt.stdout))
            print("Curl stderr:", res_non_receipt.stderr)
        
    finally:
        print("\nStopping uvicorn server...")
        proc.terminate()
        proc.wait()
        print("Server stopped.")

if __name__ == "__main__":
    test_endpoint()
