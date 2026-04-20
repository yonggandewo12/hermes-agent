# Offline Docker Deployment

## Overview

This guide describes how to build a complete, self-contained Docker image for Hermes Agent on a network-connected machine, then deploy it in an offline (air-gapped) environment with no internet access required.

## What This Produces

Running `scripts/build_offline_docker_bundle.sh` produces a `dist/docker/` directory containing:

| File | Description |
|------|-------------|
| `<tag-with-/-and-:-replaced-by-->.tar` | Complete Docker image archive |
| `<tag-with-/-and-:-replaced-by-->.tar.sha256` | SHA-256 checksum for integrity verification |
| `load-and-run.sh` | Helper script that loads the image and prints the recommended `docker run` command |
| `build-info.txt` | Build metadata (git commit, timestamp, etc.) |

The tar filename is derived from the tag by replacing `/` and `:` with `-`, then appending `.tar`. For example, `hermes-agent:offline-full` produces `hermes-agent-offline-full.tar`.

## Prerequisites

- Docker installed on the build machine
- Sufficient disk space (the full image is several GB)
- Network access for the initial build

## Build (Online Environment)

On a machine with internet access:

```bash
# Default build
./scripts/build_offline_docker_bundle.sh

# Or with custom options
./scripts/build_offline_docker_bundle.sh --tag hermes-agent:v0.8.0-offline --output-dir ./dist/docker
```

The script will:
1. Run `docker build` — this pulls all Python, npm, Playwright, and system dependencies
2. Export the image to a `.tar` file
3. Generate a SHA-256 checksum
4. Create the `load-and-run.sh` helper
5. Write build metadata to `build-info.txt`

## Transfer to Offline Environment

Copy the entire `dist/docker/` directory to the offline machine using your preferred method (USB drive, SCP over VPN, etc.).

## Load and Run (Offline Environment)

```bash
cd /path/to/dist/docker
sh load-and-run.sh
```

The script will:
1. Load the Docker image from the tar archive
2. Print the recommended `docker run` command

## Running the Container

After loading, run the container:

```bash
docker run -it --rm \
  -v $(pwd)/data:/opt/data \
  -e OPENAI_API_KEY=your_key_here \
  hermes-agent:offline-full
```

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key (or other LLM provider credentials) |

### Optional Environment Variables

See `.env.example` for the full list of supported variables.

## Verification

Verify the image integrity before loading:

```bash
cd /path/to/dist/docker
sha256sum -c hermes-agent-offline-full.tar.sha256
```

## Troubleshooting

### "docker: command not found"
Install Docker on the target machine.

### "docker: permission denied"
Ensure your user is in the `docker` group, or run with `sudo`.

### Build takes too long
The first build downloads all Python, npm, Playwright, and system dependencies. This is expected. Subsequent runs on the same machine are faster if you use Docker's layer cache.

### Image too large
This is the expected tradeoff for a fully self-contained offline image. For size optimization, consider a multi-stage Dockerfile (not in scope for this guide).

## Notes

- The image contains the complete Hermes Agent codebase and all optional dependencies (messaging, voice, Playwright, etc.)
- Do not modify files inside the image after loading — changes are lost on container restart. Use volume mounts for persistent data.
