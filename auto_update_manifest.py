"""
import os
import subprocess
import shutil
from lxml import etree  # Use lxml instead of xml.etree.ElementTree

# === CONFIGURATION ===
WORKSPACE_DIR = r"D:\AOSP3"
MANIFEST_REPO_DIR = r"D:\AOSP3\test.nes.manifest"
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
REPOS = []  # Leave empty to auto-detect

def is_git_repo(path):
    "Check if a directory is a git repository."
    return os.path.isdir(os.path.join(path, ".git"))

def get_latest_commit(repo_path):
    "Get latest commit SHA from repo_path if it's a Git repo."
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

# === Update manifest with latest commits using lxml ===
try:
    parser = etree.XMLParser(recover=True)  # recover=True handles minor malformations
    tree = etree.parse(MANIFEST_FILE, parser)
    root = tree.getroot()
except Exception as e:
    print(f"[ERROR] Failed to parse manifest: {e}")
    shutil.copy(backup_file, MANIFEST_FILE)
    print(f"[INFO] Restored manifest from backup")
    tree = etree.parse(MANIFEST_FILE, parser)
    root = tree.getroot()

for repo in REPOS:
    repo_path = os.path.join(WORKSPACE_DIR, repo)
    sha = get_latest_commit(repo_path)
    if not sha:
        continue

    updated = False
    for project in root.findall("project"):
        if project.get("path") == repo:
            project.set("revision", sha)
            print(f"[UPDATED] {repo} → {sha}")
            updated = True
            break
    if not updated:
        print(f"[WARN] {repo} not found in manifest")

tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True, pretty_print=True)

# === Commit and push ===
os.chdir(MANIFEST_REPO_DIR)

# Make sure we're not in a stuck rebase
if os.path.exists(".git/rebase-merge"):
    print("[INFO] Cleaning up previous incomplete rebase")
    subprocess.run(["git", "rebase", "--abort"], check=False)

# Ensure we’re on main (stash first to avoid conflict)
subprocess.run(["git", "stash", "--include-untracked"], check=False)
subprocess.run(["git", "checkout", "main"], check=False)

# Reapply any stashed changes
subprocess.run(["git", "stash", "pop"], check=False)

# Fetch latest remote main
subprocess.run(["git", "fetch", "origin", "main"], check=False)

# Rebase local changes on top of origin/main
subprocess.run(["git", "rebase", "origin/main"], check=False)

# Stage the manifest file
subprocess.run(["git", "add", "default.xml"], check=False)

# Commit if there are changes
if subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0:
    subprocess.run(["git", "commit", "-m", "Auto-update manifest with latest commits"], check=False)

    # 🚀 Force push directly to remote main to guarantee sync
    subprocess.run(["git", "push", "--force", "origin", "main"], check=False)
else:
    print("[INFO] No changes to commit")

print("✅ Manifest update completed and force-pushed safely to 'main'.")

"""
import os
import subprocess
import shutil
from lxml import etree

# === CONFIGURATION ===
WORKSPACE_DIR = r"D:\AOSP3"                       # Root workspace containing all repos
MANIFEST_REPO_DIR = r"D:\AOSP3\test.nes.manifest"  # Path to manifest repo
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
BRANCH = "main"

# === HELPER FUNCTIONS ===

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def get_latest_commit_local(repo_path):
    if not is_git_repo(repo_path):
        return None
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_path, text=True
        ).strip()
        return sha
    except subprocess.CalledProcessError:
        return None

def get_latest_commit_remote(repo_url, branch="main"):
    try:
        sha = subprocess.check_output(
            ["git", "ls-remote", repo_url, branch], text=True
        ).split()[0]
        return sha
    except subprocess.CalledProcessError:
        return None

def git_command(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

# === BACKUP MANIFEST ===
backup_file = MANIFEST_FILE + ".bak"
shutil.copy(MANIFEST_FILE, backup_file)
print(f"[BACKUP] Old manifest saved to {backup_file}")

# === PARSE MANIFEST ===
parser = etree.XMLParser(recover=True)
tree = etree.parse(MANIFEST_FILE, parser)
root = tree.getroot()

# === DETECT ALL REPOS ===
REPOS = []
for root_dir, dirs, files in os.walk(WORKSPACE_DIR):
    if ".git" in dirs:
        rel_path = os.path.relpath(root_dir, WORKSPACE_DIR).replace("\\", "/")
        REPOS.append(rel_path)

# === UPDATE MANIFEST ===
for project in root.findall("project"):
    repo_path = os.path.join(WORKSPACE_DIR, project.get("path").replace("/", os.sep))
    repo_url = project.get("name")
    sha = None

    if os.path.exists(repo_path) and is_git_repo(repo_path):
        sha = get_latest_commit_local(repo_path)
    else:
        # Try remote if local repo missing
        if repo_url:
            sha = get_latest_commit_remote(f"https://github.com/ck0403/{repo_url}.git", BRANCH)

    if sha:
        old_sha = project.get("revision")
        project.set("revision", sha)
        print(f"[UPDATED] {project.get('path')}: {old_sha} → {sha}")
    else:
        print(f"[WARN] Cannot get commit for {project.get('path')}")

# Write updated manifest
tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True, pretty_print=True)

# === GIT OPERATIONS ===
os.chdir(MANIFEST_REPO_DIR)

# Cleanup incomplete rebase if any
if os.path.exists(".git/rebase-merge"):
    print("[INFO] Aborting previous rebase")
    subprocess.run(["git", "rebase", "--abort"], check=False)

# Stash local changes
subprocess.run(["git", "stash", "--include-untracked"], check=False)
subprocess.run(["git", "checkout", BRANCH], check=False)
subprocess.run(["git", "stash", "pop"], check=False)

# Fetch latest remote
subprocess.run(["git", "fetch", "origin", BRANCH], check=False)

# Rebase local changes on top of origin/main
code, out, err = git_command(["git", "rebase", f"origin/{BRANCH}"])
if code != 0:
    print("[ERROR] Rebase failed. Resolve conflicts manually and continue.")
    print(err)
    exit(1)
else:
    print("[INFO] Rebase successful")

# Stage changes
subprocess.run(["git", "add", "default.xml"], check=False)

# Commit if there are changes
if subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0:
    subprocess.run(["git", "commit", "-m", "Auto-update manifest with latest commits"], check=False)
    subprocess.run(["git", "push", "--force", "origin", BRANCH], check=False)
    print("✅ Manifest updated and force-pushed to 'main'")
else:
    print("[INFO] No changes to commit")

import os
import subprocess
import shutil
from lxml import etree

# === CONFIGURATION ===
WORKSPACE_DIR = r"D:\AOSP3"                  # Root directory where repos live
MANIFEST_REPO_DIR = r"D:\AOSP3\test.nes.manifest"  # Manifest repo
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
BRANCH = "main"

# === HELPER FUNCTIONS ===
def run(cmd, cwd=None, check=False):
    #Run a shell command and return (returncode, stdout, stderr3
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def is_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))

def get_remote_commit(repo_path):
    #Get latest commit SHA from remote main of the repo
    if not is_git_repo(repo_path):
        print(f"[SKIP] {repo_path} is not a Git repo.")
        return None
    # Fetch latest remote main
    run(["git", "fetch", "origin", "main"], cwd=repo_path)
    # Get commit SHA of origin/main
    sha, _, _ = run(["git", "rev-parse", "origin/main"], cwd=repo_path)
    return sha

# === MAIN SCRIPT ===

if not os.path.exists(MANIFEST_FILE):
    print(f"[ERROR] Manifest file not found: {MANIFEST_FILE}")
    exit(1)

# Backup manifest
backup_file = MANIFEST_FILE + ".bak"
shutil.copy(MANIFEST_FILE, backup_file)
print(f"[BACKUP] Old manifest saved to {backup_file}")

# Parse XML
parser = etree.XMLParser(recover=True)
tree = etree.parse(MANIFEST_FILE, parser)
root = tree.getroot()

# Auto-detect repos in workspace
REPOS = [
    d for d in os.listdir(WORKSPACE_DIR)
    if os.path.isdir(os.path.join(WORKSPACE_DIR, d))
    and not d.startswith(".")
    and d != ".repo"
]

# Update manifest revisions from **remote commits**
for repo in REPOS:
    repo_path = os.path.join(WORKSPACE_DIR, repo)
    sha = get_remote_commit(repo_path)
    if not sha:
        continue

    updated = False
    for project in root.findall("project"):
        if project.get("path") == repo:
            project.set("revision", sha)
            print(f"[UPDATED] {repo} → {sha}")
            updated = True
            break
    if not updated:
        print(f"[WARN] {repo} not found in manifest")

# Write updated manifest
tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True, pretty_print=True)

# === GIT OPERATIONS ===
os.chdir(MANIFEST_REPO_DIR)

# Cleanup incomplete rebase if any
if os.path.exists(".git/rebase-merge") or os.path.exists(".git/rebase-apply"):
    print("[INFO] Aborting previous rebase")
    subprocess.run(["git", "rebase", "--abort"], check=False)

print("[INFO] Stashing local changes before rebase...")
stash_code, stash_out, stash_err = git_command([
    "git", "stash", "push", "--all", "-m", "pre-rebase backup"
])
if stash_code == 0:
    print(f"[INFO] Stashed changes: {stash_out.strip()}")
else:
    print(f"[WARN] Could not stash changes: {stash_err.strip()}")

# Checkout main branch
subprocess.run(["git", "checkout", BRANCH], check=True)

# Fetch latest remote
subprocess.run(["git", "fetch", "origin", BRANCH], check=True)

# Rebase local main on top of origin/main
code, out, err = git_command(["git", "rebase", f"origin/{BRANCH}"])
if code != 0:
    print("[ERROR] Rebase failed. Resolve conflicts manually and continue.")
    print(err)
    exit(1)
else:
    print("[INFO] Rebase successful")

# Pop stash if it exists
stash_list_code, stash_list_out, _ = git_command(["git", "stash", "list"])
if "pre-rebase backup" in stash_list_out:
    print("[INFO] Applying stashed changes...")
    subprocess.run(["git", "stash", "pop"], check=False)
else:
    print("[INFO] No stashed changes to apply")