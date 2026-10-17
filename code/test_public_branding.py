"""Guard the public dashboard title and reader-facing branding."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = "<title>Fraud Policy Evaluation | Payment Decisions, Disputes &amp; Recovery</title>"
BANNER = "FRAUD POLICY EVALUATION <em>/</em> PAYMENT DECISIONS, DISPUTES &amp; RECOVERY"

class PublicBrandingTests(unittest.TestCase):
    def test_public_title_and_banner_match_source_and_dashboard(self):
        for path in ("docs/v11_template.html", "docs/index.html"):
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                self.assertEqual(text.count(TITLE), 1)
                self.assertEqual(text.count(BANNER), 1)
                self.assertNotIn("D04 v11 |", text)
                self.assertNotIn("VERSION 11", text)
                self.assertNotIn("This v8 adds", text)
                self.assertNotIn("fictional D04 CSV inputs", text)
                self.assertNotIn("RELEASE_RECORD.md", text)

    def test_no_code_or_release_tag_renaming(self):
        self.assertTrue((ROOT / "code/build_v11.py").is_file())
        self.assertTrue((ROOT / "results/feedback_loop_metrics.json").is_file())
        self.assertTrue((ROOT / "CITATION.cff").is_file())

if __name__ == "__main__":
    unittest.main()
