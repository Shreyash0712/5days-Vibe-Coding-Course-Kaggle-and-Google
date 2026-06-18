import json
import base64
import urllib.request
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python send_pubsub.py <payload.json>")
        sys.exit(1)

    filename = sys.argv[1]
    
    with open(filename, 'r') as f:
        data = f.read()
        
    # Cloud Pub/Sub requires the payload to be base64 encoded
    b64_data = base64.b64encode(data.encode('utf-8')).decode('utf-8')
    
    # Wrap it in the standard Pub/Sub push envelope
    payload = {
        "message": {
            "attributes": {},
            "data": b64_data,
            "messageId": "test-local-message-123"
        },
        "subscription": "projects/my-gcp-project/subscriptions/expense-topic-sub"
    }
    
    from formatter import print_success, print_error
    
    # print(f"Sending expense payload to localhost:8080...")
    
    req = urllib.request.Request(
        "http://localhost:8080/",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode())
            print_success("HTTP 200 OK", resp_data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print_error(f"HTTP {e.code} Error", error_body)
    except Exception as e:
        print_error("Connection Error", str(e))

if __name__ == "__main__":
    main()
