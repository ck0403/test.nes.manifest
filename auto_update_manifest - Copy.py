"""
import os
import subprocess
import xml.etree.ElementTree as ET
import shutil

# === CONFIGURATION ===
WORKSPACE_DIR = r"D:\Jenkings_Test\Repo_test"
MANIFEST_REPO_DIR = r"D:\Jenkings_Test\Repo_test\test.nes.manifest"  # Adjust this path if needed
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
REPOS = []  # Leave empty to auto-detect

def is_git_repo(path):
    Check if a directory is a git repository.
    return os.path.isdir(os.path.join(path, ".git"))

def get_latest_commit(repo_path):
    "Get latest commit SHA from repo_path if it's a Git repo."
    if not is_git_repo(repo_path):
        print(f"[SKIP] {repo_path} is not a Git repo.")
        return None
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path, text=True).strip()
        return sha
    except subprocess.CalledProcessError:
        print(f"[ERROR] Cannot get commit for {repo_path}")
        return None

# === MAIN SCRIPT ===
if not os.path.exists(MANIFEST_FILE):
    print(f"[ERROR] Manifest file not found: {MANIFEST_FILE}")
    exit(1)

if not REPOS:
    REPOS = [
        d for d in os.listdir(WORKSPACE_DIR)
        if os.path.isdir(os.path.join(WORKSPACE_DIR, d))
        and not d.startswith(".")
        and d != ".repo"
    ]

# Backup manifest before modifying
backup_file = MANIFEST_FILE + ".bak"
shutil.copy(MANIFEST_FILE, backup_file)
print(f"[BACKUP] Old manifest saved to {backup_file}")

tree = ET.parse(MANIFEST_FILE)
root = tree.getroot()

for repo in REPOS:
    repo_path = os.path.join(WORKSPACE_DIR, repo)
    sha = get_latest_commit(repo_path)
    if not sha:
        continue

    for project in root.findall("project"):
        if project.attrib.get("path") == repo:
            project.set("revision", sha)
            print(f"[UPDATED] {repo} → {sha}")
            break
    else:
        print(f"[WARN] {repo} not found in manifest")

tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True)

# Commit and push manifest
os.chdir(MANIFEST_REPO_DIR)
subprocess.call(["git", "add", "default.xml"])
if subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0:
    subprocess.call(["git", "commit", "-m", "Auto-update manifest with latest commits"])
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
    ).strip()
    subprocess.call(["git", "push", "origin", branch])
else:
    print("[INFO] No changes to commit")

print("✅ Manifest update completed successfully.")
"""
import os
import subprocess
import xml.etree.ElementTree as ET
import shutil
import sys

# === CONFIGURATION ===
WORKSPACE_DIR = "D:/Jenkings_Test/Repo_test"  # Use forward slashes to avoid warnings
MANIFEST_REPO_DIR = "D:/Jenkings_Test/Repo_test/test.nes.manifest"
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
REPOS = []  # Leave empty to auto-detect

# === UTILITY FUNCTIONS ===
def is_git_repo(path):
    """Check if a directory is a git repository."""
    return os.path.isdir(os.path.join(path, ".git"))

def get_latest_commit(repo_path):
    """Get latest commit SHA from repo_path if it's a Git repo."""
    if not is_git_repo(repo_path):
        print(f"[SKIP] {repo_path} is not a Git repo.")
        return None
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_path, text=True
        ).strip()
        return sha
    except subprocess.CalledProcessError:
        print(f"[ERROR] Cannot get commit for {repo_path}")
        return None

def run_cmd(cmd, cwd=None, check=False):
    """Run a shell command and optionally fail if check=True."""
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        print(result.stderr)
        sys.exit(1)
    return result

# === MAIN SCRIPT ===
if not os.path.exists(MANIFEST_FILE):
    print(f"[ERROR] Manifest file not found: {MANIFEST_FILE}")
    exit(1)

# Auto-detect repositories if REPOS is empty
if not REPOS:
    REPOS = [
        d for d in os.listdir(WORKSPACE_DIR)
        if os.path.isdir(os.path.join(WORKSPACE_DIR, d))
        and not d.startswith(".")
        and d != ".repo"
    ]

# Backup manifest
backup_file = MANIFEST_FILE + ".bak"
shutil.copy(MANIFEST_FILE, backup_file)
print(f"[BACKUP] Old manifest saved to {backup_file}")

# === Update manifest with latest commits ===
tree = ET.parse(MANIFEST_FILE)
root = tree.getroot()

for repo in REPOS:
    repo_path = os.path.join(WORKSPACE_DIR, repo)
    sha = get_latest_commit(repo_path)
    if not sha:
        continue

    for project in root.findall("project"):
        if project.attrib.get("path") == repo:
            project.set("revision", sha)
            print(f"[UPDATED] {repo} → {sha}")
            break
    else:
        print(f"[WARN] {repo} not found in manifest")

tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True)

# === Commit and push ===
os.chdir(MANIFEST_REPO_DIR)

# Determine current branch
branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=True).stdout.strip()

# Fetch latest changes from remote
run_cmd(["git", "fetch", "origin"], check=True)

# Check for local changes
local_changes = run_cmd(["git", "diff", "--quiet"]).returncode != 0 \
                or run_cmd(["git", "diff", "--cached", "--quiet"]).returncode != 0

if local_changes:
    print("[INFO] Stashing local changes before rebase")
    run_cmd(["git", "stash", "--include-untracked"], check=True)

# Rebase onto remote
run_cmd(["git", "rebase", f"origin/{branch}"], check=True)

# Apply stashed changes if any
stash_list = run_cmd(["git", "stash", "list"]).stdout.strip()
if stash_list:
    print("[INFO] Applying stashed changes")
    run_cmd(["git", "stash", "pop"], check=True)

# Stage manifest changes
run_cmd(["git", "add", "default.xml"], check=True)

# Commit if there are changes
if run_cmd(["git", "diff", "--cached", "--quiet"]).returncode != 0:
    run_cmd(["git", "commit", "-m", "Auto-update manifest with latest commits"], check=True)
    run_cmd(["git", "push", "origin", branch], check=True)
else:
    print("[INFO] No changes to commit")

print("✅ Manifest update completed successfully.")

