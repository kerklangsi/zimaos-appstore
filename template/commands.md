# Docker CLI to Docker Compose Command-Line Reference

This document details the command-line flags recognized by the crawler and harvester, mapped directly to their equivalent service directives in `docker-compose.yml`.

The machine-readable definitions are maintained in [`template/commands.json`](https://github.com/kerklangsi/zimaos-appstore/blob/main/template/commands.json) and dynamically loaded by [`scripts/compose_harvester.py`](https://github.com/kerklangsi/zimaos-appstore/blob/main/scripts/compose_harvester.py).

---

## Command-Line Mapping Table

| Docker CLI Flag | Compose Directive | Type | Example CLI Syntax | Generated Compose YAML |
| :--- | :--- | :--- | :--- | :--- |
| `-p`, `--publish` | `ports` | `port` | `-p 8080:80` | `ports: [{target: 80, published: 8080, protocol: tcp}]` |
| `-v`, `--volume` | `volumes` | `volume` | `-v /host/dir:/data` | `volumes: [{type: bind, source: /DATA/AppData/$AppID/data, target: /data}]` |
| `-e`, `--env` | `environment` | `key_value` | `-e KEY=val` | `environment: {KEY: val}` |
| `--restart` | `restart` | `string` | `--restart unless-stopped` | `restart: unless-stopped` |
| `-u`, `--user` | `user` | `string` | `-u 1000:1000` | `user: "1000:1000"` |
| `--network`, `--net` | `network_mode` | `string` | `--network host` | `network_mode: host` |
| `--privileged` | `privileged` | `boolean` | `--privileged` | `privileged: true` |
| `--device` | `devices` | `list` | `--device /dev/dri:/dev/dri` | `devices: ["/dev/dri:/dev/dri"]` |
| `--cap-add` | `cap_add` | `list` | `--cap-add NET_ADMIN` | `cap_add: ["NET_ADMIN"]` |
| `--cap-drop` | `cap_drop` | `list` | `--cap-drop ALL` | `cap_drop: ["ALL"]` |
| `--shm-size` | `shm_size` | `string` | `--shm-size 1g` | `shm_size: 1g` |
| `-h`, `--hostname` | `hostname` | `string` | `-h myapp` | `hostname: myapp` |
| `--dns` | `dns` | `list` | `--dns 8.8.8.8` | `dns: ["8.8.8.8"]` |
| `-w`, `--workdir` | `working_dir` | `string` | `-w /app` | `working_dir: /app` |
| `-l`, `--label` | `labels` | `key_value` | `-l tier=backend` | `labels: {tier: backend}` |
| `--sysctl` | `sysctls` | `key_value` | `--sysctl net.core.somaxconn=1024` | `sysctls: {net.core.somaxconn: "1024"}` |

---

## How It Works

1. **Rule Definition**: Add or adjust flags in `template/commands.json`.
2. **Dynamic Ingestion**: When `scripts/import.py` scans applications from `apps.md`, it passes documentation markdown to `compose_harvester.py`.
3. **Extraction**: `compose_harvester.load_commands()` iterates through the registered rules and regex patterns to extract all parameters.
4. **Compose Assembly**: Extracted directives are applied to the base `template/docker-compose.yml` service block.
