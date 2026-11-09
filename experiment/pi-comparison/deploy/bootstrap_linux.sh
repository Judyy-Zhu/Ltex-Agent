#!/usr/bin/env bash
# Install pinned Linux tools inside the uploaded bundle. Never run an LLM.
set -euo pipefail
bundle_root="$(cd "${1:?Usage: bootstrap_linux.sh BUNDLE_ROOT}" && pwd)"
tools_dir="$bundle_root/.tools"
downloads="$tools_dir/downloads"
mkdir -p "$downloads"
test "$(uname -m)" = x86_64

fetch() {
  local download_url="$1" download_path="$2"
  if [[ ! -f "$download_path" ]]; then
    curl -fL --retry 3 --connect-timeout 20 -C - "$download_url" -o "$download_path.part"
    mv "$download_path.part" "$download_path"
  fi
}

node_version=25.6.1
fetch "https://nodejs.org/dist/v$node_version/node-v$node_version-linux-x64.tar.xz" "$downloads/node.tar.xz"
fetch "https://nodejs.org/dist/v$node_version/SHASUMS256.txt" "$downloads/node-SHASUMS256.txt"
python3 - "$downloads" "$node_version" <<'PY'
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]);name=f'node-v{sys.argv[2]}-linux-x64.tar.xz'
expected=next(line.split()[0] for line in (p/'node-SHASUMS256.txt').read_text().splitlines() if line.split()[-1]==name)
assert hashlib.sha256((p/'node.tar.xz').read_bytes()).hexdigest()==expected,'Node checksum mismatch'
PY
if [[ ! -x "$tools_dir/node/bin/node" ]]; then
  mkdir -p "$tools_dir/node"
  tar -xJf "$downloads/node.tar.xz" -C "$tools_dir/node" --strip-components=1
fi

fetch 'https://github.com/leanprover/lean4/releases/download/v4.35.0/lean-4.35.0-linux.tar.zst' "$downloads/lean-4.35.0-linux.tar.zst"
fetch 'https://api.github.com/repos/leanprover/lean4/releases/tags/v4.35.0' "$downloads/lean-release.json"
python3 - "$downloads" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);name='lean-4.35.0-linux.tar.zst'
asset=next(a for a in json.loads((p/'lean-release.json').read_text())['assets'] if a['name']==name)
expected=asset['digest'].removeprefix('sha256:')
h=hashlib.sha256()
with (p/name).open('rb') as f:
    for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
assert h.hexdigest()==expected,'Lean checksum mismatch'
PY
if [[ ! -x "$tools_dir/lean-4.35.0-linux/bin/lean" ]]; then
  tar --zstd -xf "$downloads/lean-4.35.0-linux.tar.zst" -C "$tools_dir"
fi

export RUSTUP_HOME="$tools_dir/rustup"
export CARGO_HOME="$tools_dir/cargo"
if [[ ! -x "$RUSTUP_HOME/toolchains/1.97.1-x86_64-unknown-linux-gnu/bin/rustc" ]]; then
  "$HOME/.cargo/bin/rustup" toolchain install 1.97.1 --profile minimal --no-self-update
fi
export PATH="$tools_dir/node/bin:$tools_dir/lean-4.35.0-linux/bin:$RUSTUP_HOME/toolchains/1.97.1-x86_64-unknown-linux-gnu/bin:$PATH"

if [[ ! -x "$bundle_root/.venv/bin/python" ]]; then
  python3 -m venv "$bundle_root/.venv" || python3 -m venv --without-pip "$bundle_root/.venv"
fi
if ! "$bundle_root/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
  fetch 'https://bootstrap.pypa.io/get-pip.py' "$downloads/get-pip.py"
  "$bundle_root/.venv/bin/python" "$downloads/get-pip.py"
fi
"$bundle_root/.venv/bin/python" -m pip install -r "$bundle_root/litex-Stoicheia/experiment/pi-comparison/deploy/requirements-linux.txt"

cd "$bundle_root/LitexGeo/golitex"
cargo build --release --locked --offline
./target/release/litex --version

cd "$bundle_root/repl"
lake build

cd "$bundle_root/Lean"
lake exe cache get Mathlib.Analysis.Real.Sqrt Mathlib.Tactic.Ring Mathlib.Tactic.Linarith Mathlib.Tactic.NormNum Mathlib.Tactic.Positivity Mathlib.Tactic.FieldSimp

cd "$bundle_root/pi"
NPM_CONFIG_USERCONFIG=/dev/null NPM_CONFIG_CACHE="$tools_dir/npm-cache" npm ci --ignore-scripts --no-audit --no-fund
bash pi-test.sh --version

cat > "$bundle_root/server-env.sh" <<'ENV'
# Source this file from any working directory. No model request is made.
EUCLID_BUNDLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export EUCLID_WORKSPACE="$EUCLID_BUNDLE_ROOT"
export EUCLID_PI_CHECKOUT="$EUCLID_BUNDLE_ROOT/pi"
export EUCLID_LAKE="$EUCLID_BUNDLE_ROOT/.tools/lean-4.35.0-linux/bin/lake"
export EUCLID_LEAN_PROJECT="$EUCLID_BUNDLE_ROOT/Lean"
export EUCLID_LEAN_REPL="$EUCLID_BUNDLE_ROOT/repl/.lake/build/bin/repl"
export EUCLID_LITEX="$EUCLID_BUNDLE_ROOT/LitexGeo/golitex/target/release/litex"
export PATH="$EUCLID_BUNDLE_ROOT/.venv/bin:$EUCLID_BUNDLE_ROOT/.tools/node/bin:$EUCLID_BUNDLE_ROOT/.tools/lean-4.35.0-linux/bin:$PATH"
ENV
printf 'Linux tools and dependencies installed; no model API called.\n'
