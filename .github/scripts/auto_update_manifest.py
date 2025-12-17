import os
import subprocess
import xml.etree.ElementTree as ET

# === CONFIGURATION ===
WORKSPACE_DIR = r"E:\AOSp"       # Root of your Repo workspace
MANIFEST_REPO_DIR = r"E:\Jenkins\test.nes.manifest"       # Path to your manifest repo
MANIFEST_FILE = os.path.join(MANIFEST_REPO_DIR, "default.xml")
REPOS = []  # Leave empty to auto-detect, or list specific repo paths relative to workspace

# === HELPER FUNCTIONS ===
def get_projects_from_manifest(MANIFEST_REPO_DIR):
    """Parse the manifest XML and return a list of project paths."""
    projects = []
    try:
        tree = ET.parse(MANIFEST_FILE)
        root = tree.getroot()
        for project in root.findall("project"):
            project_path = project.attrib.get("path")
            if project_path:
                # Build the full absolute path
                full_path = project_path.replace('/', '\\')
                projects.append(full_path)
    except ET.ParseError as e:
        print(f"Error parsing manifest XML: {e}")
    return projects

# Use the manifest to get the list of projects to update
REPOS = get_projects_from_manifest(MANIFEST_FILE)

def get_latest_commit(repo_path, branch="main", remote="origin"):
    """Get latest commit SHA from the remote server branch."""
    try:
        # Fetch latest from remote (without merging)
        subprocess.run(
            ["git", "fetch", remote, branch],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        
        # Get the remote branch commit
        sha = subprocess.check_output(
            ["git", "rev-parse", f"{remote}/{branch}"],
            cwd=repo_path
        ).decode().strip()
        
        print(f"✓ Remote commit for {os.path.basename(repo_path)}: {sha[:8]}")
        return sha
        
    except subprocess.CalledProcessError:
        # Fallback to local commit if remote fetch fails
        print(f"⚠️  Using local commit for {os.path.basename(repo_path)} (remote fetch failed)")
        try:
            sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path
            ).decode().strip()
            return sha
        except:
            print(f"❌ Cannot get any commit for {repo_path}")
            return None

def update_manifest(repo_path, sha):
    """Update the revision attribute of the project in the manifest XML."""
    tree = ET.parse(MANIFEST_FILE)
    root = tree.getroot()

    updated = False
    for project in root.findall("project"):
        path = project.attrib.get("path")
        path = path.replace('/', '\\')
        if path == repo_path:
            print("updating")
            project.set("revision", sha)
            updated = True
            print(f"Updated {path} to {sha}")

    if updated:
        tree.write(MANIFEST_FILE, encoding="utf-8", xml_declaration=True)

# === MAIN SCRIPT ===
for repo in REPOS:
    repo_path = repo
    sha = get_latest_commit(repo_path)
    if sha:
        update_manifest(repo_path, sha)

# Commit and push manifest
os.chdir(MANIFEST_REPO_DIR)
subprocess.call(["git", "add", "default.xml"])
subprocess.call(["git", "commit", "-m", "Auto-update manifest with latest commits"])
subprocess.call(["git", "push", "origin", "main"])
print("Manifest update completed.")
