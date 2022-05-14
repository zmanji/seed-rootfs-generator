A repository that uses GH Actions to create a reproducible Debian rootfs which
can be used to bootstrap / seed something more complicated.

## Creating pex.lock file

Run:
```
PEX_SCRIPT=pex3 python3 `which pex` lock create -v --no-build --indent=2 --resolver-version pip-2020-resolver --no-index --find-links 'https://github.com/zmanji/pyzstd-wheel-builder/releases/tag/v0.0.6' --platform linux_x86_64-cp-310-cp310 --platform linux_x86_64-cp-39-cp39 --platform linux_x86_64-cp-38-cp38 pyzstd
```
