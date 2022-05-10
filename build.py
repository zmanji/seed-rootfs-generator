#!/usr/bin/env python3

import io
import re
import os
import hashlib
import subprocess
import tempfile
import tarfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory() as tdir:
        tfile = tdir + "/bullseye.tar"
        e = os.environ.copy()
        e["SOURCE_DATE_EPOCH"] = "0"
        try:
            print("running mmdebstrap...")
            p = subprocess.run(
                [
                    "./mmdebstrap/mmdebstrap",
                    "--variant=buildd",
                    # Note cannot use unshare on github actions inside a docker
                    # container ?
                    "--include=python3,cmake,ninja-build",
                    "--hook-dir=./mmdebstrap/hooks/eatmydata",
                    '--aptopt=APT::Get::Install-Recommends "false"',
                    '--aptopt=APT::Get::Install-Suggests "false"',
                    "bullseye",
                    tfile,
                    "deb https://debian.notset.fr/snapshot/archive/debian/20220506T205402Z/ bullseye main",
                ],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                check=True,
                env=e,
            )
            original = tarfile.open(name=tfile)
            new = tarfile.open(
                name="./rootfs.tar",
                mode="x:",
                errorlevel=2,
                format=tarfile.PAX_FORMAT,
            )

            r = re.compile(
                r"""
            ^\./dev/.* | 
            ^\./usr/share/man/.* |
            ^\./usr/share/info/.* |
            ^\./usr/share/doc/.* |
            ^\./usr/share/locale/.* |
            ^\./usr/share/bash-completions/.* |
            ^\./usr/share/lintian/.* |
            ^\./usr/share/zoneinfo/right/.* |
            ^\./usr/share/cmake-.*/Help/.* |
            ^\./var/cache/.* |

            # These leak from the host
            ^\./etc/resolv.conf$ |
            ^\./etc/hostname$ |

            # Safe because will never run systemd
            ^\./var/lib/systemd/.* |
            ^\./etc/systemd/.* |
            ^\./lib/systemd/.* |

            # For reproducibility
            ^./usr/.*\.pyc$
                """,
                re.X,
            )

            for i in original.getmembers():
                # NOTE(zmanji): This def breaks some symlinks, should, remove
                # broken symlinks after? Audit for issues?
                if r.search(i.name):
                    continue
                if i.isfile():
                    f = original.extractfile(i)
                else:
                    f = None
                new.addfile(i, f)

            new.close()
        except subprocess.CalledProcessError as e:
            print(e.stderr)
            raise


if __name__ == "__main__":
    main()
