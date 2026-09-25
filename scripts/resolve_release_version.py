import os
import sys
import json
import subprocess

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Resolves target release tag and auto-bumps version based on commit context
def resolve_release_tag(repo_root, override_tag=None):
    cfg_path = os.path.join(repo_root, 'store-config.json')
    if not os.path.exists(cfg_path):
        return override_tag or 'v3.0.0', False

    with open(cfg_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    cur_ver = data.get('store_version', '3.0.0')

    if override_tag:
        return override_tag, False

    try:
        last_msg = subprocess.check_output(
            ['git', 'log', '-1', '--pretty=%B'],
            cwd=repo_root
        ).decode('utf-8', errors='ignore').strip()
    except Exception:
        last_msg = ''

    # If triggered by upstream apps.md sync, minor bump was already applied
    if 'chore(sync):' in last_msg or 'chore(release):' in last_msg:
        return f"v{cur_ver}", False

    parts = [int(p) if p.isdigit() else 0 for p in cur_ver.split('.')]
    while len(parts) < 3:
        parts.append(0)

    # Allow commit message hints or default to major for PC pushes
    if '[patch]' in last_msg.lower():
        new_ver = f"{parts[0]}.{parts[1]}.{parts[2] + 1}"
    elif '[minor]' in last_msg.lower():
        new_ver = f"{parts[0]}.{parts[1] + 1}.0"
    else:
        new_ver = f"{parts[0] + 1}.0.0"

    data['store_version'] = new_ver
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[VERSION] Pushed from PC - bumped version: {cur_ver} -> {new_ver}", file=sys.stderr)
    return f"v{new_ver}", True

# Program entry point to determine tag and manage version updates for CI release workflow
def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    override = None
    is_ci = False
    for arg in sys.argv[1:]:
        if arg == '--ci':
            is_ci = True
        elif not arg.startswith('--'):
            override = arg

    tag, bumped = resolve_release_tag(repo_root, override)
    if is_ci:
        print(f"tag={tag}")
        print(f"bumped={str(bumped).lower()}")
    else:
        print(tag)

if __name__ == '__main__':
    main()
