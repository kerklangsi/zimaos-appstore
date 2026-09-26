import os, sys, subprocess
from pathlib import Path
from store_utils import load_json, save_json, update_readme

# Resolves target release tag and auto-bumps version based on commit context
def release_tag(repo_root, override_tag=None):
    cfg_path = Path(repo_root) / 'store-config.json'
    if not cfg_path.exists():
        return override_tag or 'v3.0.0', False
    data = load_json(cfg_path)
    cur_ver = data.get('store_version', '3.0.0')
    if override_tag and override_tag.lower() not in ('latest', 'none', ''):
        return override_tag, False
    try:
        last_msg = subprocess.check_output(['git', 'log', '-1', '--pretty=%B'], cwd=repo_root).decode('utf-8', errors='ignore').strip()
    except Exception:
        last_msg = ''
    if 'chore(release):' in last_msg or '[skip ci]' in last_msg.lower():
        return f"v{cur_ver}", False
    p = ([int(x) if x.isdigit() else 0 for x in cur_ver.split('.')] + [0, 0])[:3]
    if '[major]' in last_msg.lower():
        new_ver = f"{p[0]+1}.0.0"
    elif '[minor]' in last_msg.lower():
        new_ver = f"{p[0]}.{p[1]+1}.0"
    else:
        new_ver = f"{p[0]}.{p[1]}.{p[2]+1}"
    data['store_version'] = new_ver
    save_json(cfg_path, data)
    update_readme(repo_root, new_ver)
    print(f"[VERSION] Pushed from PC - bumped version: {cur_ver} -> {new_ver}", file=sys.stderr)
    return f"v{new_ver}", True

# Program entry point to determine tag and manage version updates for CI release workflow
def main():
    repo_root = Path(__file__).parent.parent.resolve()
    is_ci = '--ci' in sys.argv
    override = next((a for a in sys.argv[1:] if not a.startswith('--')), None)
    tag, bumped = release_tag(repo_root, override)
    print(f"tag={tag}\nbumped={str(bumped).lower()}" if is_ci else tag)

if __name__ == '__main__':
    main()
