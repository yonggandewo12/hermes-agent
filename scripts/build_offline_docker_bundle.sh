#!/usr/bin/env bash
#
# Offline Docker bundle build script.
# Builds a Docker image and exports it as a standalone tar archive with checksums.
#
set -euo pipefail

# ── Argument parsing ──────────────────────────────────────────────────────────

TAG="${TAG:-hermes-agent:offline-full}"
OUTPUT_DIR="${OUTPUT_DIR:-dist/docker}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)      TAG="$2";      shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --dockerfile) DOCKERFILE="$2"; shift 2 ;;
    *)          echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Sanitize TAG to safe filename (replace / and : with -)
SAFE_TAG="${TAG//\//-}"
SAFE_TAG="${SAFE_TAG//:/-}"
TAR_NAME="${SAFE_TAG}.tar"

# ── Pre-flight checks ─────────────────────────────────────────────────────────

if ! command -v docker &>/dev/null; then
  echo "Error: docker command not found. Please install Docker." >&2
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "Error: Docker daemon is not accessible. Is Docker running?" >&2
  exit 1
fi

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "Error: Dockerfile not found at: $DOCKERFILE" >&2
  exit 1
fi

# ── Output directory ──────────────────────────────────────────────────────────

mkdir -p "$OUTPUT_DIR"

# ── Build metadata ────────────────────────────────────────────────────────────

GIT_REV="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HOSTNAME_VAL="$(hostname)"

{
  echo "git_revision=$GIT_REV"
  echo "git_branch=$GIT_BRANCH"
  echo "build_timestamp=$TIMESTAMP"
  echo "build_hostname=$HOSTNAME_VAL"
  echo "docker_tag=$TAG"
} > "$OUTPUT_DIR/build-info.txt"

echo "Build metadata written to $OUTPUT_DIR/build-info.txt"

# ── Docker build ──────────────────────────────────────────────────────────────

echo "Building Docker image: $TAG"
docker build -f "$DOCKERFILE" -t "$TAG" . --progress=plain

# ── Docker save ───────────────────────────────────────────────────────────────

echo "Saving Docker image to $OUTPUT_DIR/$TAR_NAME"
docker save "$TAG" -o "$OUTPUT_DIR/$TAR_NAME"

# ── SHA256 checksum ───────────────────────────────────────────────────────────

CHECKSUM=$(sha256sum "$OUTPUT_DIR/$TAR_NAME" | awk '{print $1}')
echo "$CHECKSUM  $TAR_NAME" > "$OUTPUT_DIR/$TAR_NAME.sha256"
echo "SHA256: $CHECKSUM"

# ── Generate load-and-run.sh ──────────────────────────────────────────────────

cat > "$OUTPUT_DIR/load-and-run.sh" << 'LOADER_EOF'
#!/usr/bin/env bash
#
# Offline Docker load and run helper.
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

# ── Summary output ────────────────────────────────────────────────────────────

echo ""
echo "=== Build complete ==="
echo ""
echo "Output files in $OUTPUT_DIR:"
ls -lh "$OUTPUT_DIR"
