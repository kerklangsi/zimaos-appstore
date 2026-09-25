import os
import sys
import json
import urllib.request
import urllib.error
import yaml

# Fetches raw text content from an HTTP or HTTPS URL
def fetch_url_text(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'ZimaOS-AppStore-Sync/1.0'}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')

# Merges upstream compose specifications into local CasaOS app configuration
def merge_compose_data(local_data, upstream_data):
    merged = dict(local_data) if local_data else {}

    # Update top-level compose name if provided upstream
    if 'name' in upstream_data and upstream_data['name']:
        merged['name'] = upstream_data['name']

    # Merge container services configuration
    upstream_services = upstream_data.get('services', {})
    local_services = merged.get('services', {})

    if upstream_services:
        for svc_name, upstream_svc in upstream_services.items():
            if svc_name in local_services:
                local_svc = local_services[svc_name]
                # Update image tag
                if 'image' in upstream_svc:
                    local_svc['image'] = upstream_svc['image']
                # Update environment variables
                if 'environment' in upstream_svc:
                    local_svc['environment'] = upstream_svc['environment']
                # Update ports
                if 'ports' in upstream_svc:
                    local_svc['ports'] = upstream_svc['ports']
                # Update network mode & restart policy
                if 'network_mode' in upstream_svc:
                    local_svc['network_mode'] = upstream_svc['network_mode']
                if 'restart' in upstream_svc:
                    local_svc['restart'] = upstream_svc['restart']
                
                # Merge volume targets while keeping local host $AppID paths
                if 'volumes' in upstream_svc and isinstance(upstream_svc['volumes'], list):
                    merged_vols = []
                    local_vols = local_svc.get('volumes', [])
                    for up_vol in upstream_svc['volumes']:
                        if isinstance(up_vol, dict):
                            target = up_vol.get('target')
                            # Find matching local volume by target container path
                            matched = next((lv for lv in local_vols if isinstance(lv, dict) and lv.get('target') == target), None)
                            if matched and '$AppID' in str(matched.get('source', '')):
                                merged_vols.append(matched)
                            else:
                                merged_vols.append(up_vol)
                        else:
                            merged_vols.append(up_vol)
                    local_svc['volumes'] = merged_vols
            else:
                local_services[svc_name] = upstream_svc
        merged['services'] = local_services

    # Preserve or update x-casaos metadata
    upstream_casaos = upstream_data.get('x-casaos', {})
    local_casaos = merged.get('x-casaos', {})

    if upstream_casaos:
        # If upstream defines x-casaos, merge version and release notes
        for k, v in upstream_casaos.items():
            if v:
                local_casaos[k] = v
    else:
        # If upstream lacks x-casaos, inspect image tag for semver update
        for _, svc in upstream_services.items():
            img = svc.get('image', '')
            if ':' in img:
                tag = img.split(':')[-1]
                if tag.startswith('v') and any(c.isdigit() for c in tag):
                    clean_ver = tag.lstrip('v')
                    local_casaos['version'] = clean_ver

    merged['x-casaos'] = local_casaos
    return merged

# Synchronizes all configured upstream applications with local compose files
def sync_all_apps(config_path):
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return 0

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    updated_count = 0
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for app_id, app_info in config.items():
        name = app_info.get('name', app_id)
        upstream_url = app_info.get('upstream_url')
        target_compose = os.path.join(repo_root, app_info.get('target_compose'))

        print(f"\n[SYNC] Checking '{name}' ({app_id})...")
        print(f"       Upstream: {upstream_url}")

        try:
            upstream_text = fetch_url_text(upstream_url)
            upstream_data = yaml.safe_load(upstream_text)
            if not isinstance(upstream_data, dict):
                print(f"       [SKIP] Upstream YAML did not parse to a dictionary.")
                continue

            local_data = {}
            if os.path.exists(target_compose):
                with open(target_compose, 'r', encoding='utf-8') as f:
                    local_data = yaml.safe_load(f) or {}

            merged_data = merge_compose_data(local_data, upstream_data)
            merged_yaml = yaml.dump(merged_data, sort_keys=False, allow_unicode=True, indent=2)

            existing_yaml = ""
            if os.path.exists(target_compose):
                with open(target_compose, 'r', encoding='utf-8') as f:
                    existing_yaml = f.read()

            # Compare parsed data to prevent unnecessary whitespace diffs
            if yaml.safe_load(existing_yaml) != merged_data:
                os.makedirs(os.path.dirname(target_compose), exist_ok=True)
                with open(target_compose, 'w', encoding='utf-8') as f:
                    f.write(merged_yaml)
                print(f"       [UPDATED] Successfully updated {target_compose}")
                updated_count += 1
            else:
                print(f"       [UP-TO-DATE] No changes detected.")

        except urllib.error.HTTPError as he:
            print(f"       [WARN] HTTP {he.code} when fetching upstream: {he.reason}")
        except Exception as e:
            print(f"       [ERROR] Failed to sync '{app_id}': {e}")

    print(f"\n[SYNC COMPLETE] Total applications updated: {updated_count}")
    return updated_count

# Program entry point for executing upstream store synchronization
def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_file = os.path.join(repo_root, 'upstream-apps.json')
    sync_all_apps(config_file)

if __name__ == '__main__':
    main()
