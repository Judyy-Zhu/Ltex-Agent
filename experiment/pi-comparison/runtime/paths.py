"""Resolve the original workstation tree or a self-contained server bundle."""
import os
from pathlib import Path
import shutil

BASE=Path(__file__).resolve().parents[1]
PROJECT=BASE.parents[1]
bundle=PROJECT.parent
default_workspace=bundle if (bundle/'Lean').is_dir() and (bundle/'LitexGeo').is_dir() else BASE.parents[3]
WORKSPACE=Path(os.environ.get('EUCLID_WORKSPACE',default_workspace)).resolve()
PI=Path(os.environ.get('EUCLID_PI_CHECKOUT',WORKSPACE/'pi' if (WORKSPACE/'pi').is_dir() else WORKSPACE/'Stoicheia/pi')).resolve()
LEAN_PROJECT=Path(os.environ.get('EUCLID_LEAN_PROJECT',WORKSPACE/'Lean')).resolve()
LAKE=Path(os.environ.get('EUCLID_LAKE',shutil.which('lake') or Path.home()/'.elan/bin/lake')).absolute()
REPL=Path(os.environ.get('EUCLID_LEAN_REPL',WORKSPACE/'repl/.lake/build/bin/repl' if (WORKSPACE/'repl').is_dir() else WORKSPACE/'lean_auto_build_system/scripts/.tools/repl/.lake/build/bin/repl')).resolve()
LITEX=Path(os.environ.get('EUCLID_LITEX',WORKSPACE/'LitexGeo/golitex/target/release/litex')).resolve()
