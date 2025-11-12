import os
import subprocess
import shutil
from lxml import etree
import sys

# === CONFIGURATION ===
WORKSPACE_DIR = r"D:\AOSP2"                  # Root directory where repos live
MANIFEST_REPO_DIR = r"D:\AOSP2\test.nes.manifest"  # Manifest repo
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
REPOS = []

for root_dir, dirs, files in os.walk(WORKSPACE_DIR):
    # Skip .repo folder entirely
    if ".repo" in dirs:
        dirs.remove(".repo")
    
    # If this folder contains a .git directory, it's a repo
    if ".git" in dirs:
        rel_path = os.path.relpath(root_dir, WORKSPACE_DIR).replace("\\", "/")
        REPOS.append(rel_path)

# Update manifest revisions from **remote commits**
for repo in REPOS:
    repo_path = os.path.join(WORKSPACE_DIR, repo)
    sha = get_remote_commit(repo_path)
    if not sha:
        continue
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed with exit code {e.returncode}")
        print("Try running:")
        print("git config --global --add safe.directory D:/AOSp/test.nes.manifest")
        sys.exit(1)

    updated = False
    for project in root.findall("project"):
        if project.get("path") == repo:
            project.set("revision", str(sha))
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

# Helper for git commands
def git_command(cmd):
    return run(cmd, cwd=MANIFEST_REPO_DIR)

# Cleanup incomplete rebase if any
if os.path.exists(".git/rebase-merge") or os.path.exists(".git/rebase-apply"):
    print("[INFO] Aborting previous rebase")
    git_command(["git", "rebase", "--abort"])

# Step 1: Stash all local changes including untracked files
print("[INFO] Stashing local changes before rebase...")
stash_code, stash_out, stash_err = git_command(["git", "stash", "push", "--all", "-m", "pre-rebase backup"])
if stash_code == 0:
    print(f"[INFO] Stashed changes: {stash_out.strip()}")
else:
    print(f"[WARN] Could not stash changes: {stash_err.strip()}")

# Step 2: Checkout main branch
git_command(["git", "checkout", BRANCH])

# Step 3: Fetch latest from origin
git_command(["git", "fetch", "origin", BRANCH])

# Step 4: Rebase local main on top of origin/main
rebase_code, rebase_out, rebase_err = git_command(["git", "rebase", f"origin/{BRANCH}"])
if rebase_code != 0:
    print("[ERROR] Rebase failed. Resolve conflicts manually and continue.")
    print(rebase_err)
    exit(1)
else:
    print("[INFO] Rebase successful")

# Step 5: Pop stashed changes
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

# Step 6: Stage & commit changes if any
git_command(["git", "add", "."])
diff_code, _, _ = git_command(["git", "diff", "--cached", "--quiet"])
if diff_code != 0:
    git_command(["git", "commit", "-m", "Auto-update manifest with latest commits"])
    print("[INFO] Changes committed.")
else:
    print("[INFO] No changes to commit")

# Step 7: Push to origin
git_command(["git", "push", "origin", BRANCH])
print("[INFO] Push completed.")
