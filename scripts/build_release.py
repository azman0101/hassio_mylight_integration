#!/usr/bin/env python3
"""Build deterministic HACS release assets without third-party dependencies."""
from __future__ import annotations
import hashlib, json, sys, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"custom_components"/"mylight_systems"
DIST=ROOT/"dist"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build() -> None:
    DIST.mkdir(exist_ok=True)
    manifest=json.loads((SOURCE/"manifest.json").read_text())
    expected=sys.argv[1].removeprefix("v") if len(sys.argv)>1 else manifest["version"]
    if manifest["version"]!=expected:
        raise SystemExit(f"manifest version {manifest['version']} does not match release {expected}")
    archive=DIST/"mylight_systems.zip"
    files=[p for p in sorted(SOURCE.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for path in files:
            info=zipfile.ZipInfo(path.relative_to(SOURCE).as_posix(),date_time=(1980,1,1,0,0,0))
            info.external_attr=0o100644<<16; info.compress_type=zipfile.ZIP_DEFLATED
            output.writestr(info,path.read_bytes())
    sbom={"spdxVersion":"SPDX-2.3","dataLicense":"CC0-1.0","SPDXID":"SPDXRef-DOCUMENT","name":f"mylight_systems-{expected}","documentNamespace":f"https://github.com/azman0101/hassio_mylight_integration/releases/tag/v{expected}","creationInfo":{"creators":["Tool: scripts/build_release.py"],"created":"1980-01-01T00:00:00Z"},"packages":[{"name":"mylight_systems","SPDXID":"SPDXRef-Package","versionInfo":expected,"downloadLocation":"NOASSERTION","filesAnalyzed":False}]}
    (DIST/"mylight_systems.spdx.json").write_text(json.dumps(sbom,indent=2,sort_keys=True)+"\n")
    assets=(archive,DIST/"mylight_systems.spdx.json")
    (DIST/"SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in assets))

if __name__=="__main__": build()
