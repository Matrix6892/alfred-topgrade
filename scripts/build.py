#!/usr/bin/env python3
"""Build a deterministic, source-inclusive Alfred import file."""
import argparse
from pathlib import Path
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from install import ROOT, package_files


def build(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, source in sorted(package_files().items()):
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = (0o100755 if name == "run.sh" else 0o100644) << 16
            archive.writestr(entry, source.read_bytes())
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Topgrade.alfredworkflow")
    print(build(parser.parse_args().output))
