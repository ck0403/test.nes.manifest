import xml.etree.ElementTree as ET
import argparse
import datetime
import sys
import os
from pathlib import Path

def update_default_xml(commit_hash, branch, message, date):
    """Update default.xml with commit information"""
    
    xml_file = Path("default.xml")
    
    # Create default.xml if it doesn't exist
    if not xml_file.exists():
        print(f"📄 Creating {xml_file} as it doesn't exist...")
        root = ET.Element("project")
        tree = ET.ElementTree(root)
        
        # Add basic structure
        name_elem = ET.SubElement(root, "name")
        name_elem.text = "Project Manifest"
        
        commit_info = ET.SubElement(root, "commit-info")
        history = ET.SubElement(root, "commit-history")
        
        tree.write(xml_file, encoding='utf-8', xml_declaration=True)
    
    try:
        # Parse XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Update commit-info element
        commit_info = root.find('commit-info')
        if commit_info is None:
            commit_info = ET.SubElement(root, 'commit-info')
        
        commit_info.set('hash', commit_hash)
        commit_info.set('branch', branch)
        commit_info.set('date', date)
        commit_info.set('message', message[:100])  # Truncate long messages
        commit_info.set('updated', datetime.datetime.now().isoformat())
        
        # Add to commit history
        history = root.find('commit-history')
        if history is None:
            history = ET.SubElement(root, 'commit-history')
        
        # Create new commit entry
        commit_entry = ET.SubElement(history, 'commit')
        commit_entry.set('hash', commit_hash)
        commit_entry.set('branch', branch)
        commit_entry.set('date', date)
        commit_entry.set('message', message[:100])
        
        # Keep only last 20 commits in history
        all_commits = history.findall('commit')
        if len(all_commits) > 20:
            for old_commit in all_commits[:-20]:
                history.remove(old_commit)
        
        # Write back to file
        tree.write(xml_file, encoding='utf-8', xml_declaration=True)
        
        print(f"✅ Updated {xml_file} with commit {commit_hash[:8]}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating {xml_file}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Update default.xml with commit info')
    parser.add_argument('--commit', required=True, help='Commit hash')
    parser.add_argument('--branch', required=True, help='Branch name')
    parser.add_argument('--message', required=True, help='Commit message')
    parser.add_argument('--date', required=True, help='Commit date')
    
    args = parser.parse_args()
    
    update_default_xml(
        commit_hash=args.commit,
        branch=args.branch,
        message=args.message,
        date=args.date
    )

if __name__ == '__main__':
    main()