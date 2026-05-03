import tempfile
import unittest
from pathlib import Path

from Experiments.common.claim_audit import audit_files


class ClaimAuditTests(unittest.TestCase):
    def test_flags_dual_modal_as_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "content.tex"
            paper.write_text("Our system uses Dual-Modal Retrieval as the core contribution.\n", encoding="utf-8")

            findings = audit_files([paper])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 1)
        self.assertEqual(findings[0]["pattern"], "Dual-Modal Retrieval")
        self.assertIn("multimodal claim", findings[0]["reason"])

    def test_flags_revision_memo_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "supplementary.tex"
            paper.write_text("The current codebase uses a server-side artifact snapshot.\n", encoding="utf-8")

            findings = audit_files([paper])

        patterns = {finding["pattern"] for finding in findings}
        self.assertEqual(patterns, {"current codebase", "server-side"})

    def test_clean_narrow_claim_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "content.tex"
            paper.write_text(
                "We study texture-aware retrieval for executable guitar-effect preset selection.\n",
                encoding="utf-8",
            )

            findings = audit_files([paper])

        self.assertEqual(findings, [])

    def test_reports_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paper = Path(tmp_dir) / "content.tex"
            paper.write_text("This demonstrates real-time deployment.\n", encoding="utf-8")

            findings = audit_files([paper])

        self.assertEqual(findings[0]["file"], str(paper))
        self.assertEqual(findings[0]["pattern"], "real-time deployment")


if __name__ == "__main__":
    unittest.main()
