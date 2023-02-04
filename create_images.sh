#!/bin/bash
docker build -f Dockerfile.dev . --tag cyborgfi/askgpt:dev
docker build -f Dockerfile . --tag cyborgfi/askgpt:latest
