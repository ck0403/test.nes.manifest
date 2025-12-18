import os
import subprocess
import shutil
from lxml import etree
import sys

# === CONFIGURATION ===
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))                # Root directory where repos live
print(WORKSPACE_DIR)
MANIFEST_REPO_DIR = os.path.join(os.getcwd()) # Manifest repo
print(MANIFEST_REPO_DIR)
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
BRANCH = "main"

# === HELPER FUNCTIONS ===
def run(cmd, cwd=None, check=False):
    """Run a shell command and return (returncode, stdout, stderr)"""
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def is_git_repo(path):
    """Check if path is a git repo (directory or submodule)"""
    git_path = os.path.join(path, ".git")
    return os.path.isdir(git_path) or os.path.isfile(git_path)

def get_remote_commit(repo_path):
    """Get latest commit SHA from remote main of the repo"""
    if not is_git_repo(repo_path):
        print(f"[SKIP] {repo_path} is not a Git repo.")
        return None
    # Fetch latest remote main
    run(["git", "fetch", "origin", "main"], cwd=repo_path)
    # Get commit SHA of origin/main
    _, sha, _ = run(["git", "rev-parse", "origin/main"], cwd=repo_path)
    return sha

# === MAIN SCRIPT ===

if not os.path.exists(MANIFEST_FILE):
    print(f"[ERROR] Manifest file not found: {MANIFEST_FILE}")
    sys.exit(1)

# Backup manifest
backup_file = MANIFEST_FILE + ".bak"
shutil.copy(MANIFEST_FILE, backup_file)
print(f"[BACKUP] Old manifest saved to {backup_file}")

# Parse XML
parser = etree.XMLParser(recover=True)
tree = etree.parse(MANIFEST_FILE, parser)
root = tree.getroot()

# Auto-detect repos in workspace
REPOS = []

for root_dir, dirs, files in os.walk(WORKSPACE_DIR):
    if ".repo" in dirs:
        dirs.remove(".repo")
    if is_git_repo(root_dir):
        rel_path = os.path.relpath(root_dir, WORKSPACE_DIR).replace("\\", "/")
        REPOS.append(rel_path)

# Update manifest revisions from remote commits
updated_projects = []
for repo in REPOS:
    repo_path = os.path.join(WORKSPACE_DIR, repo)
    sha = get_remote_commit(repo_path)
    if not sha:
        continue

    updated = False
    for project in root.findall("project"):
        if project.get("path") == repo:
            old_sha = project.get("revision")
            if old_sha != sha:
                project.set("revision", sha)
                updated_projects.append((repo, old_sha, sha))
            updated = True
            break
    if not updated:
        print(f"[WARN] {repo} not found in manifest")

# Show manifest updates
if updated_projects:
    print("\n[INFO] Updated manifest projects (old → new):")
    for repo, old_sha, new_sha in updated_projects:
        print(f"  {repo}: {old_sha} → {new_sha}")
else:
    print("\n[INFO] No changes in manifest")

# Write updated manifest
tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True, pretty_print=True)

# === GIT OPERATIONS ===
os.chdir(MANIFEST_REPO_DIR)

def git_command(cmd):
    return run(cmd, cwd=MANIFEST_REPO_DIR)

# Cleanup incomplete rebase
if os.path.exists(".git/rebase-merge") or os.path.exists(".git/rebase-apply"):
    print("[INFO] Aborting previous rebase")
    git_command(["git", "rebase", "--abort"])

# Stash changes
print("[INFO] Stashing local changes before rebase...")
stash_code, stash_out, stash_err = git_command(["git", "stash", "push", "--all", "-m", "pre-rebase backup"])
if stash_code == 0:
    print(f"[INFO] Stashed changes: {stash_out.strip()}")
else:
    print(f"[WARN] Could not stash changes: {stash_err.strip()}")

# Checkout and rebase
git_command(["git", "checkout", BRANCH])
git_command(["git", "fetch", "origin", BRANCH])
rebase_code, rebase_out, rebase_err = git_command(["git", "rebase", f"origin/{BRANCH}"])
if rebase_code != 0:
    print("[ERROR] Rebase failed. Resolve conflicts manually and continue.")
    print(rebase_err)
    sys.exit(1)
print("[INFO] Rebase successful")

# Apply stash if exists
stash_list_code, stash_list_out, _ = git_command(["git", "stash", "list"])
if "pre-rebase backup" in stash_list_out:
    print("[INFO] Applying stashed changes...")
    pop_code, pop_out, pop_err = git_command(["git", "stash", "pop"])
    if pop_code == 0:
        print(f"[INFO] Applied stash: {pop_out.strip()}")
    else:
        print(f"[WARN] Could not apply stash: {pop_err.strip()}")
else:
    print("[INFO] No stashed changes to apply")

# Stage only changed manifest
git_command(["git", "add", MANIFEST_FILE])

# Show staged files
_, staged_files_out, _ = git_command(["git", "diff", "--cached", "--name-only"])
staged_files = staged_files_out.splitlines()
if staged_files:
    print("\n[INFO] Files to be added:")
    for f in staged_files:
        print(f"  {f}")
else:
    print("\n[INFO] No manifest changes detected")

# Show git status
_, status_out, _ = git_command(["git", "status", "--short"])
print("\n[INFO] Git status after staging:")
print(status_out.strip() if status_out.strip() else "(clean)")

# Commit & push if changes
if staged_files:
    git_command(["git", "commit", "-m", "Auto-update manifest with latest commits"])
    git_command(["git", "push", "origin", BRANCH])
    print("[INFO] Changes committed and pushed.")
else:
    print("[INFO] No changes to commit")
