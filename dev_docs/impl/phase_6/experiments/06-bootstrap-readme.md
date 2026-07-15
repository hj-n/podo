# Experiment 06 — Bootstrap and README

## Question

README의 실제 명령만으로 설치, update, rollback과 hook 검토까지 이해할 수 있는가?

## Status

Bootstrap passed on 2026-07-15; public README activation waits for the first verified GitHub Release.

## Evidence

- Generated `install.sh` downloads only the selected semantic-version archive and checksum from the fixed public Release path.
- It validates an exact 64-character lowercase SHA-256 before extraction.
- The inline extractor accepts only relative regular files/directories and writes them beneath a disposable directory.
- A Workspace path containing spaces installs correctly through the standalone package installer.
- Damaged checksum fails before Workspace creation.
- Test Release base override requires `PODO_TEST_RELEASES=1`; the published default remains `github.com/hj-n/podo`.

## Remaining

Publish and download the real asset, then replace README's local-development-only installation section with the verified public command.
