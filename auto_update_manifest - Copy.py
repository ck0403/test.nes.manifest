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
    """Check if a directory is a git repository."""
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

# === CONFIGURATION ===
WORKSPACE_DIR = r"D:\Jenkings_Test\Repo_test"
MANIFEST_REPO_DIR = r"D:\Jenkings_Test\Repo_test\test.nes.manifest"
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
REPOS = []  # Leave empty to auto-detect

def is_git_repo(path):
    """Check if a directory is a git repository."""
    return os.path.isdir(os.path.join(path, ".git"))

def get_latest_commit(repo_path):
    """Get latest commit SHA from repo_path if it's a Git repo."""
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

# Parse manifest and update revisions
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

# Commit and push manifest safely
os.chdir(MANIFEST_REPO_DIR)

# Pull latest remote changes first
branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
subprocess.call(["git", "fetch", "origin"])
subprocess.call(["git", "rebase", f"origin/{branch}"])

# Stage and commit changes
subprocess.call(["git", "add", "default.xml"])
if subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0:
    subprocess.call(["git", "commit", "-m", "Auto-update manifest with latest commits"])
    # Push after rebasing
    subprocess.call(["git", "push", "origin", branch])
else:
    print("[INFO] No changes to commit")

print("✅ Manifest update completed successfully.")
