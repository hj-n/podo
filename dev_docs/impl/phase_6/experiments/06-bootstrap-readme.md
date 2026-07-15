# Experiment 06 — Bootstrap and README

## Question

README의 실제 명령만으로 설치, update, rollback과 hook 검토까지 이해할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- Generated `install.sh` downloads only the selected semantic-version archive and checksum from the fixed public Release path.
- It validates an exact 64-character lowercase SHA-256 before extraction.
- The inline extractor accepts only relative regular files/directories and writes them beneath a disposable directory.
- A Workspace path containing spaces installs correctly through the standalone package installer.
- Damaged checksum fails before Workspace creation.
- Test Release base override requires `PODO_TEST_RELEASES=1`; the published default remains `github.com/hj-n/podo`.

- README now exposes the exact anonymous `releases/latest/download/install.sh` command only after v0.5.0 was downloaded and installed from GitHub successfully.
- Requirements, custom Workspace path, hook review/trust, latest update, exact rollback, doctor/recover and product/user ownership are documented at user level.
