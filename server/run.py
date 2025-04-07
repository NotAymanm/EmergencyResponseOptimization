import os
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Ottawa Emergency Services Data Processing and API")
    parser.add_argument('--preprocess', action='store_true', help="Run data preprocessing only")
    parser.add_argument('--api', action='store_true', help="Run FastAPI server only")
    parser.add_argument('--port', type=int, default=8000, help="Port for the FastAPI server")
    
    args = parser.parse_args()
    
    # Check if arguments are provided
    if not (args.preprocess or args.api):
        print("No arguments provided. Running both preprocessing and API server.")
        args.preprocess = True
        args.api = True
    
    # Create directories if they don't exist
    if not os.path.exists("processed_data"):
        os.makedirs("processed_data")
    
    # Run data preprocessing if requested
    if args.preprocess:
        print("Running data preprocessing...")
        subprocess.run(["python", "data_processing.py"])
    
    # Run FastAPI server if requested
    if args.api:
        print(f"Starting FastAPI server on port {args.port}...")
        subprocess.run(["uvicorn", "api:app", "--host", "0.0.0.0", "--port", str(args.port)])

if __name__ == "__main__":
    main()