#!/bin/bash
python3 -m build && \
gpg --detach-sign -a dist/askGPT-0.7.7.tar.gz && \
twine upload dist/askGPT-0.7.7.tar.gz dist/askGPT-0.7.7.tar.gz.asc
