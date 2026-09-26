import os, re, yaml

# Extracts docker-compose YAML code blocks from markdown documentation
def extract_compose(md_text):
    if not md_text:
        return None
    for block in re.findall(r'```(?:yaml|docker-compose|yml)?\s*\n([\s\S]*?)\n```', md_text, re.IGNORECASE):
        if 'services:' in block:
            try:
                parsed = yaml.safe_load(block)
                if isinstance(parsed, dict) and ('services' in parsed or 'name' in parsed):
                    return parsed
            except Exception:
                pass
    return None

# Parses docker flags and keywords from markdown text into structured container config
def parse_run(md_text, app_id, default_image):
    if not md_text:
        return {}
    cleaned = re.sub(r'\\\r?\n\s*', ' ', md_text)
    env_vars, volumes, ports = {}, [], []
    restart_policy, user_val, network_val = 'unless-stopped', None, None

    for m in re.finditer(r'(?:-e|--env)\s+["\']?([A-Za-z0-9_]+)=([^"\'\s\\]+)["\']?', cleaned):
        k, v = m.group(1), m.group(2).strip('`$;')
        if not v.startswith('$') or v == '$AppID':
            env_vars[k] = v

    for m in re.finditer(r'(?:-v|--volume)\s+["\']?([^"\'\s]+):([^"\'\s:]+)["\']?', cleaned):
        _, target = m.group(1), m.group(2).strip('`$;')
        if target.startswith('/') and len(target) > 1:
            sub = os.path.basename(target.rstrip('/')) or 'data'
            if not any(v.get('target') == target for v in volumes):
                volumes.append({'type': 'bind', 'source': f'/DATA/AppData/$AppID/{sub}', 'target': target})

    for m in re.finditer(r'(?:-p|--publish)\s+["\']?([0-9]+(?::[0-9]+)?)["\']?', cleaned):
        p = m.group(1).strip()
        parts = p.split(':') if ':' in p else [p, p]
        if parts[0].isdigit() and parts[1].isdigit():
            ports.append({'target': int(parts[1]), 'published': int(parts[0]), 'protocol': 'tcp'})

    u_match = re.search(r'(?:--user|-u)\s+["\']?([0-9]+:[0-9]+|[a-zA-Z0-9_\-]+)["\']?', cleaned)
    user_val = u_match.group(1).strip() if u_match else None
    r_match = re.search(r'--restart\s+["\']?(always|unless-stopped|on-failure|no)["\']?', cleaned)
    restart_policy = r_match.group(1).strip() if r_match else 'unless-stopped'
    n_match = re.search(r'--network\s+["\']?([a-zA-Z0-9_\-]+)["\']?', cleaned)
    network_val = n_match.group(1).strip() if n_match else None

    res = {'environment': env_vars, 'volumes': volumes, 'ports': ports, 'restart': restart_policy}
    if user_val:
        res['user'] = user_val
    if network_val:
        res['network_mode'] = network_val
    return res

# Harvests docker-compose YAML and docker run commands from markdown documentation
def harvest_compose(md_text, app_id, default_image):
    compose_data = extract_compose(md_text) or {
        'name': app_id, 'services': {app_id: {'image': default_image, 'container_name': app_id, 'restart': 'unless-stopped', 'network_mode': 'bridge'}}
    }
    services = compose_data.setdefault('services', {})
    if not services:
        services[app_id] = {'image': default_image, 'container_name': app_id, 'restart': 'unless-stopped', 'network_mode': 'bridge'}

    main_svc = services[next(iter(services.keys()))]
    if 'image' not in main_svc or not main_svc['image'] or main_svc['image'] in (app_id, f"{app_id}:tag"):
        main_svc['image'] = default_image
    main_svc.setdefault('container_name', app_id)
    main_svc.setdefault('network_mode', 'bridge')

    run_data = parse_run(md_text, app_id, default_image)
    main_svc.setdefault('restart', run_data.get('restart', 'unless-stopped'))

    env_map = {}
    cur_env = main_svc.get('environment', {})
    if isinstance(cur_env, dict):
        env_map.update(cur_env)
    elif isinstance(cur_env, list):
        for item in cur_env:
            if isinstance(item, str) and '=' in item:
                k, v = item.split('=', 1)
                env_map[k] = v
    for k, v in run_data.get('environment', {}).items():
        env_map.setdefault(k, v)
    if env_map:
        main_svc['environment'] = env_map

    cur_vols = main_svc.get('volumes', [])
    vol_list = [v if isinstance(v, dict) else ({'type': 'bind', 'source': v.split(':', 1)[0], 'target': v.split(':', 1)[1]} if isinstance(v, str) and ':' in v else v) for v in (cur_vols if isinstance(cur_vols, list) else [])]
    for rv in run_data.get('volumes', []):
        if not any(v.get('target') == rv['target'] for v in vol_list if isinstance(v, dict)):
            vol_list.append(rv)
    if vol_list:
        main_svc['volumes'] = vol_list

    cur_ports = main_svc.get('ports', [])
    port_list = [p if isinstance(p, dict) else ({'target': int(p.split(':')[1]), 'published': int(p.split(':')[0]), 'protocol': 'tcp'} if isinstance(p, str) and ':' in p else p) for p in (cur_ports if isinstance(cur_ports, list) else [])]
    for rp in run_data.get('ports', []):
        if not any(p.get('target') == rp['target'] for p in port_list if isinstance(p, dict)):
            port_list.append(rp)
    if port_list:
        main_svc['ports'] = port_list

    return compose_data
