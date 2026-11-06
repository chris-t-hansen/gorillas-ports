# Security Notes

Log of security-relevant observations for this project. The game itself is a
local, offline pygame application: no network access, no `eval`/`exec`, no
file persistence, no deserialization of untrusted data, and CLI args are
handled via `argparse`. No secrets are present in the repo or git history.

## Fixed (2026-11-06)

1. **appimagetool download is now checksum-verified** (`build_appimage.sh`)
   - AppImageKit only publishes rolling `continuous` builds (no version tags),
     so the script pins SHA-256 checksums per architecture and fails closed on
     mismatch, for both fresh downloads and pre-existing local copies.
   - If the upstream `continuous` build is updated, verification will fail.
     That is intentional: independently verify the new build (e.g. against
     AppImageKit release announcements), then update `APPIMAGETOOL_SHA256`.
   - Current pinned checksums (downloaded from
     `https://github.com/AppImage/AppImageKit/releases/download/continuous/`):
     - x86_64:  `b90f4a8b18967545fda78a445b27680a1642f1ef9488ced28b65398f2be7add2`
     - aarch64: `a48972e5ae91c944c5a7c80214e7e0a42dd6aa3ae979d8756203512a74ff574d`

2. **Dependencies pinned** (`requirements.txt`, `build.sh`, `build.ps1`)
   - `pygame-ce==2.5.8`, `numpy==2.5.4`, `pyinstaller==6.22.3` — exact pins
     instead of floating `>=` ranges, for reproducible builds and to avoid
     silently pulling in a future compromised/buggy release.
   - `build.sh` now installs `requirements.txt` into fresh venvs (it
     previously only installed PyInstaller).
   - Note: the pygame community project has begun publishing under the
     `pygame` distribution name (2.6.x+). If you migrate off `pygame-ce`,
     re-pin deliberately and re-test.

3. **UPX disabled** (`gorillas.spec`)
   - `upx=False`: UPX-compressed PyInstaller binaries commonly trigger
     antivirus false positives and are harder to inspect forensically.

## Informational (no action taken)

- `build.sh` / `build.ps1` *echo* the Homebrew `curl | bash` install command
  as documentation; it is never executed by the scripts.
- The generated `AppRun` prepends the bundled lib dir to `LD_LIBRARY_PATH`.
  This is standard AppImage practice and safe here since the game spawns no
  child processes.
- The `--appimage-extract` fallback in `build_appimage.sh` (used when FUSE is
  unavailable) leaves a `squashfs-root/` directory behind; it is untracked but
  not currently in `.gitignore`.
- Consider `pip install --require-hashes` with a full lockfile (including
  transitive deps) if stronger supply-chain guarantees are needed.
- Distributed artifacts (`*.AppImage`, `dist/`, `build/`) are unsigned. If the
  project publishes releases, consider signing them and publishing checksums.
