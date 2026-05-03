from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List


FORBIDDEN_PATTERNS = {
    "Dual-Modal Retrieval": "multimodal claim is not supported as a main contribution",
    "multimodal agent": "multimodal claim is not supported as a main contribution",
    "robust multimodal": "multimodal claim is not supported as a main contribution",
    "real-time deployment": "latency evidence is not sufficient for deployment-level real-time claims",
    "current codebase": "revision-memo language should not appear in the paper",
    "verified artifact set": "revision-memo language should not appear in the paper",
    "server-side": "internal execution provenance should be moved to lab notes",
    "journal readers often care": "meta-commentary should not appear in the paper",
    "upon acceptance": "release promises should not replace reproducibility details",
}


def audit_files(paths: Iterable[Path]) -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern, reason in FORBIDDEN_PATTERNS.items():
                if pattern in line:
                    findings.append(
                        {
                            "file": str(path),
                            "line": line_no,
                            "pattern": pattern,
                            "reason": reason,
                            "text": line.strip(),
                        }
                    )
    return findings
