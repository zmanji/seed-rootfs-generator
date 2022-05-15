#!/usr/bin/env python3

import io
import re
import os
import hashlib
import gzip
import subprocess
import tempfile
import tarfile
from pathlib import Path

import pyzstd

# TODO(zmanji): Use mirror:// protocol of apt
APT_SOURCE = """
# deb https://debian.notset.fr/snapshot/archive/debian/20220510T155316Z/ bullseye main
deb https://snapshot.debian.org/archive/debian/20220510T155316Z/ bullseye main
"""


def main():
    deb_cache = Path("./deb-cache")

    proxysolver = Path("./proxysolver")
    proxysolver.symlink_to('./mmdebstrap/proxysolver')

    with tempfile.TemporaryDirectory() as tdir:
        tfile = tdir + "/bullseye.tar"

        sources = Path(tdir + "/sources.list")
        sources.write_bytes(APT_SOURCE.encode())

        e = os.environ.copy()
        e["SOURCE_DATE_EPOCH"] = "0"
        print("running mmdebstrap...", flush=True)
        p = subprocess.run(
            [
                "sudo",
                "./mmdebstrap/mmdebstrap",
                "--verbose",
                # Machinery to preserve the .debs downloaded so they can be
                # synced in the cache. This doesn't preserve 'essential' debs but good
                # enough for a speedup.
                "--skip=essential/unlink",
                "-skip=download/empty",
                '--setup-hook=mkdir -p "$1"/var/cache/apt/archives/',
                "--setup-hook=cp " + str(deb_cache) + "/base-files_*.deb \"$1\"/var/cache/apt/archives/ || true",
                "--essential-hook=cp " + str(deb_cache) + "/*.deb \"$1\"/var/cache/apt/archives/ || true",
                "--essential-hook=ls -lah \"$1\"/var/cache/apt/archives/",
                "--customize-hook=rm -rf " + str(deb_cache) +  "/* && " + " cp \"$1\"/var/cache/apt/archives/*.deb " + str(deb_cache),
                # end machinery
                "--variant=buildd",
                "--include=python3,cmake,ninja-build,ca-certificates",
                "--hook-dir=./mmdebstrap/hooks/eatmydata",
                "bullseye",
                tfile,
                str(sources),
            ],
            stdin=subprocess.DEVNULL,
            text=True,
            check=True,
            env=e,
        )

        print("Filtering tarball...")

        original = tarfile.open(name=tfile)
        buffer = io.BytesIO()
        new = tarfile.open(
            fileobj=buffer,
            mode="w:",
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
        # See https://gitlab.mister-muffin.de/josch/mmdebstrap/issues/26
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
        original.close()

        print("Creating compressed tarball...")

        d = {
            pyzstd.CParameter.compressionLevel: 15,
            pyzstd.CParameter.contentSizeFlag: 1,
            pyzstd.CParameter.checksumFlag: 1,
        }
        Path("./rootfs.tar.zst").write_bytes(
            pyzstd.richmem_compress(buffer.getvalue(), level_or_option=d),
        )
        print("Done...")


if __name__ == "__main__":
    main()
