import sys
import json

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            # Allow execution if no input is provided
            sys.exit(0)
            
        payload = json.loads(input_data)
        
        # Extract the command line from the tool arguments
        arguments = payload.get("arguments", {})
        command_line = arguments.get("CommandLine", "").lower()
        
        # List of forbidden destructive patterns
        forbidden_patterns = [
            "rm -rf /",
            "rm -rf *",
            "del /s /q",
            "format c:"
        ]
        
        for pattern in forbidden_patterns:
            if pattern in command_line:
                print(f"Error: Execution blocked. Destructive pattern detected: '{pattern}'")
                sys.exit(1)
                
        # Command is considered safe
        print("Command validation passed.")
        sys.exit(0)
        
    except json.JSONDecodeError:
        print("Error: Invalid JSON payload provided to hook script.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
