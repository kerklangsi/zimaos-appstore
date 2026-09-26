# ✔ AMP-dockerized – with Docker Desktop & Docker-out-of-Docker

**AMP-dockerized** bundles *CubeCoders AMP* into a Debian-based Docker image
(`kerklangsi/amp-docker:latest`) to make deploying and managing game servers simple and consistent inside containers.

**AMP (Application Management Panel)** provides a full web UI for creating and managing multiple game servers.
A valid **CubeCoders AMP Licence** is required to use this image.

This image now includes enhanced support for:

### **Docker Desktop (Windows/macOS)**

* Supports Docker integration via the Docker Desktop TCP endpoint.
* Works even though Docker Desktop does not expose a real `docker` group or usable Docker socket permissions.
* Enables AMP to manage containers when `DOCKER_HOST=tcp://host.docker.internal:2375` is provided and
  *“Expose daemon on tcp://localhost:2375 without TLS”* is enabled in Docker Desktop settings.

### **Docker-out-of-Docker (DooD)**

* The container includes a full Docker CLI and a mount-rewriting wrapper.

* When running on native Linux, you can mount the Docker socket:

  ```
  -v /var/run/docker.sock:/var/run/docker.sock
  ```

AMP can launch and control game server containers directly through the host Docker engine.

This is a **community-maintained, unofficial** image and is **not endorsed by CubeCoders**. 

More information at:
parent [MitchTalmadge/AMP-dockerized](https://github.com/MitchTalmadge/AMP-dockerized)
child [kerklangsi/AMP-dockerized](https://github.com/kerklangsi/AMP-dockerized)