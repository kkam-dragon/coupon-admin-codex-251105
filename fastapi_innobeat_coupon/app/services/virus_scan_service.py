from __future__ import annotations

import shlex
import subprocess
import tempfile

from app.core.config import settings


class VirusScanError(RuntimeError):
    pass


def scan_bytes(data: bytes, filename: str | None = None) -> None:
    if not settings.virus_scan_enabled:
        return
    if not settings.virus_scan_command:
        raise VirusScanError("VIRUS_SCAN_COMMAND 설정이 필요합니다.")
    if not data:
        raise VirusScanError("빈 파일은 업로드할 수 없습니다.")

    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        cmd = _build_command(tmp.name)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise VirusScanError(
                "바이러스 검사에 실패했습니다: " + (result.stderr.strip() or result.stdout.strip())
            )


def _build_command(file_path: str) -> list[str]:
    raw = settings.virus_scan_command or ""
    parts = shlex.split(raw)
    if "{file}" in parts:
        return [part.replace("{file}", file_path) for part in parts]
    if parts:
        return parts + [file_path]
    return [file_path]
