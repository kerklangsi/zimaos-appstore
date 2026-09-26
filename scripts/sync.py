import os, sys, yaml
from pathlib import Path
from store_utils import load_json, fetch_text, sync_compose, bump_version

# Synchronizes all configured upstream applications with local compose files
def sync_apps(config_path):
    if not os.path.exists(config_path):
        return 0
    config, updated_count = load_json(config_path), 0
    repo_root = Path(__file__).parent.parent.resolve()

    for app_id, app_info in config.items():
        name, url = app_info.get('name', app_id), app_info.get('upstream_url')
        target_compose = repo_root / app_info.get('target_compose', '')
        print(f"\n[SYNC] Checking '{name}' ({app_id})...\n       Upstream: {url}")
        try:
            up_text = fetch_text(url, timeout=30)
            up_data = yaml.safe_load(up_text)
            if isinstance(up_data, dict):
                changed, msg = sync_compose(target_compose, up_data)
                print(f"       [{'UPDATED' if changed else 'UP-TO-DATE'}] {msg}")
                updated_count += int(changed)
        except Exception as e:
            print(f"       [ERROR] Failed to sync '{app_id}': {e}")

    print(f"\n[SYNC COMPLETE] Total applications updated: {updated_count}")
    if updated_count > 0:
        bump_version(repo_root, bump_type='patch')
    return updated_count

# Program entry point for executing upstream store synchronization
def main():
    repo_root = Path(__file__).parent.parent.resolve()
    sync_apps(repo_root / 'upstream-apps.json')

if __name__ == '__main__':
    main()
