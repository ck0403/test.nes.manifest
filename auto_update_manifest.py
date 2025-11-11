import os
import subprocess
import xml.etree.ElementTree as ET

# === CONFIGURATION ===
WORKSPACE_DIR = r"D:\Jenkings_Test\Repo_test"       # Root of your Repo workspace
MANIFEST_REPO_DIR = r"D:\Jenkings_Test\Repo_test\.repo"       # Path to your manifest repo
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
REPOS = []  # Leave empty to auto-detect, or list specific repo paths relative to workspace

# === HELPER FUNCTIONS ===
def get_latest_commit(repo_path):
    """Get latest commit SHA from the main branch of a repo."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_path
        ).decode().strip()
        return sha
    except subprocess.CalledProcessError:
        print(f"Error: Cannot get commit for {repo_path}")
        return None

def update_manifest(repo_path, sha):
    """Update the revision attribute of the project in the manifest XML."""
    tree = ET.parse(MANIFEST_FILE)
    root = tree.getroot()

    updated = False
    for project in root.findall("project"):
        path = project.attrib.get("path")
        if path == repo_path:
            project.set("revision", sha)
            updated = True
            print(f"Updated {path} to {sha}")

    if updated:
        tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True)

# === MAIN SCRIPT ===
if not REPOS:
    # Auto-detect all top-level folders in workspace (ignore hidden dirs)
    REPOS = [
        d for d in os.listdir(WORKSPACE_DIR)
        if os.path.isdir(os.path.join(WORKSPACE_DIR, d)) and not d.startswith(".")
    ]

for repo in REPOS:
    repo_path = os.path.join(WORKSPACE_DIR, repo)
    sha = get_latest_commit(repo_path)
    if sha:
        update_manifest(repo, sha)

# Commit and push manifest
os.chdir(MANIFEST_REPO_DIR)
subprocess.call(["git", "add", "default.xml"])
subprocess.call(["git", "commit", "-m", "Auto-update manifest with latest commits"])
subprocess.call(["git", "push", "origin", "main"])

print("Manifest update completed.")
