#!/usr/bin/env python3

import hashlib
import sys
from pathlib import Path

def main():
    file = sys.argv[1]
    content = Path(file).read_bytes()

    b2 = hashlib.blake2b(content).hexdigest()
    sha = hashlib.sha256(content).hexdigest()

    notes = (
        f"Checksums for {file}\n"
        f"SHA256: {sha}\n"
        f"BLAKE2: {b2}\n"
    )

    print(notes)


if __name__ == "__main__":
    main()
