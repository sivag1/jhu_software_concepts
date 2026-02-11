"""
Module to orchestrate the full data processing pipeline.

This script runs the scraper, cleaner, LLM processor, and data loader in sequence.
It handles execution of subprocesses and error checking.
"""
import subprocess
import sys
import os

def run_step(script_name, script_path, args=None):
    """
    Runs a python script and checks for errors.

    Args:
        script_name (str): Display name of the step.
        script_path (str): Absolute path to the script file.
        args (list, optional): List of command-line arguments.

    Raises:
        FileNotFoundError: If the script path does not exist.
        RuntimeError: If the subprocess returns a non-zero exit code.
    """
    print(f"--- Starting: {script_name} ---")
    
    if not os.path.exists(script_path):
        print(f"Error: File not found at {script_path}")
        raise FileNotFoundError(f"File not found at {script_path}")
        
    try:
        # Run the script using the current python interpreter
        # We inherit the current environment and working directory
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        result = subprocess.run(cmd, check=True)
        print(f"--- Finished: {script_name} ---\n")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running {script_name}. Exit code: {e.returncode}")
        raise RuntimeError(f"Script {script_name} failed with exit code {e.returncode}")

def run_full_pipeline():
    """Executes the complete data pipeline: Scrape -> Clean -> LLM -> Load."""
    # Get the directory where this script is located (module_3)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Run scrape.py
    # Path: module_3/subprocess/scrape.py
    scrape_path = os.path.join(base_dir, "subprocess", "scrape.py")
    run_step("Scraper (scrape.py)", scrape_path)

    # 2. Run clean.py
    # Path: module_3/subprocess/clean.py
    clean_path = os.path.join(base_dir, "subprocess", "clean.py")
    run_step("Cleaner (clean.py)", clean_path)

    # 3. Run llm_hosting/app.py
    # Path: module_3/subprocess/llm_hosting/app.py
    llm_app_path = os.path.join(base_dir, "subprocess", "llm_hosting", "app.py")
    llm_args = ["--file", "cleaned_applicant_data.json", "--out", "llm_extend_applicant_data.json"]
    run_step("LLM Processing (llm_hosting/app.py)", llm_app_path, args=llm_args)

    # 4. Run load_new_data.py
    # Path: module_3/load_new_data.py
    load_data_path = os.path.join(base_dir, "load_new_data.py")
    run_step("Data Loader (load_new_data.py)", load_data_path)

    print("Pipeline completed successfully.")

if __name__ == "__main__":
    try:
        run_full_pipeline()
    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        sys.exit(1)