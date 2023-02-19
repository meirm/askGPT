#!/bin/bash
python3 -m build && \
gpg --detach-sign -a dist/askGPT-0.4.24.tar.gz && \
twine upload dist/askGPT-0.4.24.tar.gz dist/askGPT-0.4.24.tar.gz.asc
