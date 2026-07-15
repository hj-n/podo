# Experiment 02 — Reproducible Package

## Question

같은 source에서 byte-identical하고 제품 이외 자료가 없는 package를 만들 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- `python3 tests/run_phase6_release_builder.py` builds the same source twice and compares every asset hash.
- Tar entries are sorted and normalized to fixed uid, gid, mtime and mode; gzip mtime and filename are empty/fixed.
- The suite rejects links and verifies that pycache, local install manifest, development files and user Context are absent.
- The archive contains only `product/`, standalone `install.py` and internal `release.json`; the output adds checksum, bootstrap and external metadata.
