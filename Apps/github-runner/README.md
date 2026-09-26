# 🚀 GitHub Runner Manager v3.2.0

A modern, full-stack Web GUI and Docker container manager for GitHub Actions self-hosted runners. Easily provision, monitor, control, and update multiple GitHub runner instances from a high-performance web dashboard.

[![Docker Image](https://img.shields.io/docker/v/kerklangsi/github-runner?label=Docker%20Hub&color=0969da)](https://hub.docker.com/r/kerklangsi/github-runner)
[![GitHub Release](https://img.shields.io/github/v/release/kerklangsi/github-runner?color=238636)](https://github.com/kerklangsi/github-runner/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- **🌐 Modern Web Dashboard**: React + Express UI running on port 3000 for managing all runner instances in real-time.
- **⚡ Rapid Runner Provisioning**: Provision repository or organization runners using Personal Access Tokens (PAT) or one-time registration tokens.
- **📦 Unified Persistent Tool Cache**: Automatically caches toolchains (Node.js, Python via `setup-python`/`setup-node`) and packages (pip wheels, Playwright browsers, npm) into a single persistent cache volume (`/home/runner/.cache` ➔ `/opt/hostedtoolcache`), eliminating duplicate downloads across workflows.
- **📁 Decoupled Shared Repository Data**: Dedicated persistent storage (`/opt/shared_data`) organized by repository, with automatic workspace pre-linking for authentication tokens and credentials.
- **🖥️ Built-in Interactive Web Terminal**: Execute diagnostics directly from the web shell.
- **📊 Real-time Hardware Telemetry**: Monitor CPU, RAM, Disk space, and network bandwidth cgroup metrics.
- **📜 Live Log Streaming**: Inspect isolated runner logs and global container buffers with real-time level filtering (INFO, DEBUG, WARN, ERROR).
- **📋 Workflow Execution Tracking**: Track recent GitHub Actions workflow runs and completion states.
- **📁 Files & Storage Explorer**: Built-in web explorer with interactive breadcrumbs to browse, preview, and download files across `/opt/shared_data`, runner workspaces, and `/app/data`.
- **🔄 Session-Clean Log Archiving**: Clean logs on container startup and runner restarts, automatically archiving previous session logs into `/app/data/archive/` and `<runnerDir>/logs/archive/`.
- **⚡ Two-Tier Watchdog & Auto-Start**: Global master switch with per-runner watchdog recovery and optional automatic runner startup on container boot.
- **🛡️ Alert Webhooks**: Discord/Slack webhook notifications on runner crashes, offline events, or watchdog recoveries.
- **📋 Universal Clipboard Compatibility**: Robust clipboard copy fallback supporting plain HTTP LAN IP access.
- **💾 Config Backup & Restore**: Export and import system configurations as JSON.
- **🎨 Dark / Light Themes & Custom Avatars**: Customize profile avatar image URLs or base64 uploads.
- **🚀 Automatic Update Checker**: Notifies users in-app when new releases are pushed to GitHub or Docker Hub.
- **🖥️ ZimaOS & CasaOS App Store Ready**: Fully supports `x-casaos` native app store manifests.

---

## ⚡ Quickstart

### Option 1: Docker Hub Image (Recommended)

Run the pre-built image directly from Docker Hub:

```bash
docker run -d \
  --name github-runner-manager \
  --restart unless-stopped \
  -p 3000:3000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /DATA/AppData/github-runner/data:/app/data \
  -v /DATA/AppData/github-runner/runners:/opt/github-runners \
  -v /DATA/AppData/github-runner/shared_data:/opt/shared_data \
  -v /DATA/AppData/github-runner/cache:/home/runner/.cache \
  kerklangsi/github-runner:latest
```

Access the Web Dashboard at **`http://localhost:3000`** (or `http://<your-server-ip>:3000`).

---

### Option 2: Docker Compose

```yaml
version: '3.8'

services:
  github-runner-manager:
    image: kerklangsi/github-runner:latest
    container_name: github-runner-manager
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - type: bind
        source: /var/run/docker.sock
        target: /var/run/docker.sock
      - type: bind
        source: /DATA/AppData/github-runner/data
        target: /app/data
      - type: bind
        source: /DATA/AppData/github-runner/runners
        target: /opt/github-runners
      - type: bind
        source: /DATA/AppData/github-runner/shared_data
        target: /opt/shared_data
      - type: bind
        source: /DATA/AppData/github-runner/cache
        target: /home/runner/.cache
```

Launch with:
```bash
docker compose up -d
```

---

### Option 3: ZimaOS / CasaOS App Store

This repository includes a native `x-casaos` manifest for **ZimaOS** and **CasaOS** App Stores.

1. Open **ZimaOS App Store** or **CasaOS App Store**.
2. Click **Manual Install** or **Custom Install** (or install directly from the community App Store).
3. Load [`Apps/github-runner/docker-compose.yml`](Apps/github-runner/docker-compose.yml).
4. Click **Install**. ZimaOS will configure ports, persistent storage binds, icons, and shortcuts automatically!

---

## 🛠️ Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PORT` | Web GUI and API server port | `3000` |
| `DATA_DIR` | Persistent database and settings storage | `/app/data` |
| `RUNNERS_DIR` | Working directory for provisioned runners | `/opt/github-runners` |
| `SHARED_DATA_DIR` | Persistent shared repository storage | `/opt/shared_data` |
| `RUNNER_TOOL_CACHE` | Unified tool cache location | `/opt/hostedtoolcache` |

---

## 🔒 Security & Persistence

- All runner metadata, encrypted access tokens, system logs, and custom avatars are safely persisted inside the `/app/data` Docker volume mount.
- Password change forms in the Settings tab allow changing the default `admin` credentials immediately.

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

---

Made with ❤️ by [Kerk Langsi](https://github.com/kerklangsi).
