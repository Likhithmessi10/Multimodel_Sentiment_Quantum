"""
verify_isolation.py - Rigorous Safety Verification Script for PulsePress Q.

Verifies that the original source repository (C:\\projects\\news-aggregator)
has NOT been modified in any way:
- Checks file existence
- Compares SHA-256 checksums
- Compares file sizes
- Verifies no new files were created and no original files were deleted
"""

import os
import json
import hashlib
import sys


def compute_sha256(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"ERROR: {e}"


def verify_isolation():
    new_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    baseline_path = os.path.join(new_project_root, "baseline_inventory.json")
    source_root = r"C:\projects\news-aggregator"

    if not os.path.exists(baseline_path):
        print(f"[-] Fatal: Baseline inventory file not found at {baseline_path}")
        sys.exit(1)

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline_files = json.load(f)

    print("=" * 80)
    print("ISOLATION INTEGRITY & SAFETY VERIFICATION")
    print("=" * 80)
    print(f"[*] Original Source Root: {source_root}")
    print(f"[*] Total Files Monitored: {len(baseline_files)}")
    print("-" * 80)

    # Normalize baseline inventory keys
    normalized_baseline = {
        os.path.normpath(k).replace("\\", "/"): v for k, v in baseline_files.items()
    }

    # 1. Check current files in source_root
    current_files = {}
    for root, dirs, files in os.walk(source_root):
        # Skip git, pytest cache, python bytecode caches, and venv
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "node_modules", ".pytest_cache")]
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                continue
            abs_p = os.path.join(root, f)
            rel_p = os.path.relpath(abs_p, source_root).replace("\\", "/")
            current_files[rel_p] = abs_p

    mismatches = []
    missing_files = []
    hash_differences = []
    size_differences = []

    for rel_path, meta in normalized_baseline.items():
        full_path = os.path.join(source_root, os.path.normpath(rel_path))
        if not os.path.exists(full_path):
            missing_files.append(rel_path)
            continue

        curr_size = os.path.getsize(full_path)
        base_size = meta["size_bytes"]
        if curr_size != base_size:
            size_differences.append({
                "file": rel_path,
                "baseline_size": base_size,
                "current_size": curr_size
            })

        curr_sha = compute_sha256(full_path)
        base_sha = meta["sha256"]
        if curr_sha != base_sha:
            hash_differences.append({
                "file": rel_path,
                "baseline_sha256": base_sha,
                "current_sha256": curr_sha
            })

    # Check for newly added files in source_root
    new_files = [f for f in current_files if f not in normalized_baseline]

    print(f"[*] Missing Files         : {len(missing_files)}")
    print(f"[*] Size Discrepancies    : {len(size_differences)}")
    print(f"[*] SHA-256 Checksum Diff : {len(hash_differences)}")
    print(f"[*] Unexpected New Files  : {len(new_files)}")
    print("-" * 80)

    if not missing_files and not size_differences and not hash_differences and not new_files:
        print("[+] SUCCESS: ISOLATION 100% PRESERVED!")
        print("[+] The original project (C:\\projects\\news-aggregator) is completely intact and untouched.")
        print("=" * 80)
        return True
    else:
        print("[-] VIOLATION: Discrepancies detected in original project!")
        if missing_files:
            print(f"  Missing: {missing_files}")
        if size_differences:
            print(f"  Size diffs: {size_differences}")
        if hash_differences:
            print(f"  Hash diffs: {hash_differences}")
        if new_files:
            print(f"  New files: {new_files}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = verify_isolation()
    if not success:
        sys.exit(1)
