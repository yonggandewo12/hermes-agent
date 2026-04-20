# Offline Docker Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a one-shot script that builds the complete Hermes Agent Docker image on a network-connected machine and exports a self-contained offline delivery bundle (tar + checksum + load script + build metadata). Update docs to cover the offline deployment flow.

**Architecture:** Single shell script wrapping `docker build` + `docker save` with standard Unix tools. No new dependencies beyond Docker itself. Output goes to a configurable `dist/docker/` directory.

**Tech Stack:** Bash (POSIX), Docker CLI, `sha256sum`, standard Unix utilities (`date`, `git` if available).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/build_offline_docker_bundle.sh` | Create | One-shot build & export script |
| `docs/deployment/offline-docker.md` | Create | Full offline deployment guide |
| `README.md` | Modify | Add "Offline Docker Bundle" section |
| `README.zh-CN.md` | Modify | Add "离线 Docker 交付" section |

---

## Task 1: Write `scripts/build_offline_docker_bundle.sh`

**Files:**
- Create: `scripts/build_offline_docker_bundle.sh`

- [ ] **Step 1: Write the script header and argument parsing**

```bash
#!/usr/bin/env bash
#
# Build offline Docker bundle for Hermes Agent.
# Usage: ./scripts/build_offline_docker_bundle.sh [--tag <tag>] [--output-dir <dir>] [--dockerfile <path>]
#
set -euo pipefail

TAG="${TAG:-hermes-agent:offline-full}"
OUTPUT_DIR="${OUTPUT_DIR:-dist/docker}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --tag)
      TAG="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --dockerfile)
      DOCKERFILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Sanitize TAG to safe filename (replace / and : with -)
TAR_NAME="$(echo "$TAG" | sed 's/[\/:]/-/g')-offline.tar"
```

- [ ] **Step 2: Add pre-flight checks**

```bash
echo "=== Pre-flight checks ==="

if ! command -v docker &>/dev/null; then
  echo "Error: docker command not found. Please install Docker." >&2
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "Error: Docker daemon is not running or not accessible." >&2
  exit 1
fi

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "Error: Dockerfile not found at: $DOCKERFILE" >&2
  exit 1
fi

echo "Pre-flight checks passed."
```

- [ ] **Step 3: Add output directory, git info, and build info generation**

```bash
echo "=== Preparing output directory ==="
mkdir -p "$OUTPUT_DIR"

echo "=== Gathering build metadata ==="
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
BUILD_TIME="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
HOSTNAME="$(hostname 2>/dev/null || echo 'unknown')"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"

cat > "$OUTPUT_DIR/build-info.txt" <<EOF
image_tag=$TAG
tar_file=$TAR_NAME
dockerfile=$DOCKERFILE
git_commit=$GIT_COMMIT
build_time=$BUILD_TIME
hostname=$HOSTNAME
branch=$BRANCH
EOF

echo "Build info written to $OUTPUT_DIR/build-info.txt"
```

- [ ] **Step 4: Add Docker build step**

```bash
echo "=== Building Docker image: $TAG ==="
echo "This may take a while on first run (downloads all dependencies)..."

docker build -f "$DOCKERFILE" -t "$TAG" . --progress=plain

echo "Build complete: $TAG"
```

- [ ] **Step 5: Add Docker save and checksum**

```bash
echo "=== Exporting image to tar: $TAR_NAME ==="
docker save "$TAG" -o "$OUTPUT_DIR/$TAR_NAME"

echo "=== Generating sha256 checksum ==="
sha256sum "$OUTPUT_DIR/$TAR_NAME" | awk '{print $1}' > "$OUTPUT_DIR/$TAR_NAME.sha256"

echo "Checksum written to $OUTPUT_DIR/$TAR_NAME.sha256"
```

- [ ] **Step 6: Add load-and-run.sh generation**

```bash
echo "=== Generating load-and-run.sh ==="
cat > "$OUTPUT_DIR/load-and-run.sh" <<'LOADER_EOF'
#!/usr/bin/env bash
#
# Offline Docker load and run helper.
# This script loads the bundled Docker image and prints the recommended run command.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAR_FILE="$(ls "$SCRIPT_DIR"/*.tar 2>/dev/null | head -n1)"

if [[ -z "$TAR_FILE" ]]; then
  echo "Error: No .tar file found in $(basename "$SCRIPT_DIR")." >&2
  exit 1
fi

echo "Loading Docker image from $(basename "$TAR_FILE")..."
docker load -i "$TAR_FILE"

echo ""
echo "=== Image loaded successfully ==="
echo ""
echo "Recommended run command:"
echo ""
echo "  docker run -it --rm \"
echo "    -v \$(pwd)/data:/opt/data \"
echo "    -e OPENAI_API_KEY=your_key_here \"
echo "    hermes-agent:offline-full"
echo ""
echo "Adjust volume mounts and environment variables as needed for your deployment."
LOADER_EOF

chmod +x "$OUTPUT_DIR/load-and-run.sh"
echo "load-and-run.sh written to $OUTPUT_DIR/load-and-run.sh"
```

- [ ] **Step 7: Add final summary output and commit**

After the load-and-run.sh block, add the summary block:

```bash
echo ""
echo "=== Build complete ==="
echo ""
echo "Deliverable directory: $OUTPUT_DIR"
echo "Files:"
ls -lh "$OUTPUT_DIR"
echo ""
echo "Copy the '$OUTPUT_DIR' directory to your offline environment."
echo "Then run: sh $OUTPUT_DIR/load-and-run.sh"
```

- [ ] **Step 8: Test the script locally (dry-run syntax check only)**

Run: `bash -n scripts/build_offline_docker_bundle.sh`  
Expected: No syntax errors

- [ ] **Step 9: Commit**

```bash
git add scripts/build_offline_docker_bundle.sh
git commit -m "feat: add offline Docker bundle build script"
```

---

## Task 2: Write `docs/deployment/offline-docker.md`

**Files:**
- Create: `docs/deployment/offline-docker.md`

- [ ] **Step 1: Write the complete documentation**

Create `docs/deployment/offline-docker.md` with the following content:

```markdown
# Offline Docker Deployment

## Overview

This guide describes how to build a complete, self-contained Docker image for Hermes Agent on a network-connected machine, then deploy it in an offline (air-gapped) environment with no internet access required.

## What This Produces

Running `scripts/build_offline_docker_bundle.sh` produces a `dist/docker/` directory containing:

| File | Description |
|------|-------------|
| `<tag>-offline.tar` | Complete Docker image archive |
| `<tag>-offline.tar.sha256` | SHA-256 checksum for integrity verification |
| `load-and-run.sh` | Helper script that loads the image and prints the recommended `docker run` command |
| `build-info.txt` | Build metadata (git commit, timestamp, etc.) |

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
```

- [ ] **Step 2: Commit**

```bash
git add docs/deployment/offline-docker.md
git commit -m "docs: add offline Docker deployment guide"
```

---

## Task 3: Update `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find insertion point and add "Offline Docker Bundle" section**

Find a suitable location (after the Docker section if it exists, or before "Development"). Add:

```markdown
## Offline Docker Bundle

Build a complete, self-contained Docker image on a network-connected machine, then deploy it in an offline environment with no internet access required.

### Build (online machine)

```bash
./scripts/build_offline_docker_bundle.sh
```

This produces a `dist/docker/` directory containing the image tar, checksum, load script, and build metadata. See [docs/deployment/offline-docker.md](docs/deployment/offline-docker.md) for full details.

### Deploy (offline machine)

```bash
cd dist/docker
sh load-and-run.sh
```

The image includes all Python, npm, and Playwright dependencies — no network access needed at runtime.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add offline Docker bundle section to README"
```

---

## Task 4: Update `README.zh-CN.md`

**Files:**
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Find insertion point and add "离线 Docker 交付" section**

Find a suitable location (after the Docker section if it exists, or before "Development"). Add:

```markdown
## 离线 Docker 交付

在联网环境中构建一个包含完整依赖的 Docker 镜像，传输到离线环境后无需任何网络即可加载运行。

### 构建（联网机器）

```bash
./scripts/build_offline_docker_bundle.sh
```

脚本会在 `dist/docker/` 目录下产出镜像 tar 包、校验文件、加载脚本和构建元信息。详细说明见 [docs/deployment/offline-docker.md](docs/deployment/offline-docker.md)。

### 部署（离线机器）

```bash
cd dist/docker
sh load-and-run.sh
```

镜像已包含所有 Python、npm 和 Playwright 依赖，运行时无需任何网络连接。
```

- [ ] **Step 2: Commit**

```bash
git add README.zh-CN.md
git commit -m "docs: add offline Docker bundle section to README.zh-CN"
```

---

## Verification Summary

After all tasks:

1. `bash -n scripts/build_offline_docker_bundle.sh` — no syntax errors
2. `docs/deployment/offline-docker.md` — file exists and covers full workflow
3. `README.md` — new section present and accurate
4. `README.zh-CN.md` — new section present and accurate
5. All 4 commits exist in git history
