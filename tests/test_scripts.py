import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import arena_count  # noqa: E402
import check_claims  # noqa: E402
import run_evals  # noqa: E402

MIB = 1024 * 1024


def region(start, size, perms, name, rss):
    return (f"{start:012x}-{start + size:012x} {perms} 00000000 00:00 0 {name}\n"
            f"Size: {size // 1024} kB\nRss: {rss} kB\n")


class ArenaCount(unittest.TestCase):
    def test_counts_only_arena_sized_anonymous_rw_regions(self):
        text = (region(0x1000000000, 64 * MIB, "rw-p", "", 40000)
                + region(0x2000000000, 64 * MIB, "rw-p", "", 8000)
                + region(0x3000000000, 256 * MIB, "rw-p", "", 300000)
                + region(0x4000000000, 64 * MIB, "r--p", "", 1000)
                + region(0x5000000000, 64 * MIB, "rw-p", "/lib/x.so", 1000))
        result = arena_count.summarize(arena_count.parse(text.splitlines()))
        self.assertEqual(result["arena_like_regions"], 2)
        self.assertAlmostEqual(result["arena_like_rss_mib"], 48000 / 1024)


class CheckClaims(unittest.TestCase):
    def test_repository_claims_pass_offline(self):
        claims = json.loads((ROOT / "claims.json").read_text())["claims"]
        self.assertEqual(check_claims.check_offline(claims, ROOT), [])

    def test_detects_bad_tag_unknown_source_and_missing_phrase(self):
        bad = [{"id": "x", "text": "t", "tag": "Z", "source_id": "NOPE", "file": "SKILL.md", "phrase": "zzz-not-there"}]
        errors = check_claims.check_offline(bad, ROOT)
        self.assertEqual(len(errors), 3)

    def test_online_check_reports_changed_content(self):
        claims = [{"id": "c", "url": "http://example.invalid", "expect": "hello"}]
        self.assertEqual(check_claims.check_online(claims, fetcher=lambda u: "Hello world"), [])
        self.assertEqual(len(check_claims.check_online(claims, fetcher=lambda u: "bye")), 1)


class RunEvals(unittest.TestCase):
    def test_parses_every_case_in_prompts_file(self):
        cases = run_evals.parse_prompts((ROOT / "evals" / "prompts.md").read_text())
        self.assertEqual(len(cases), 9)
        for case in cases:
            self.assertTrue(case["prompt"], case["title"])
            self.assertTrue(case["must"], case["title"])

    def test_grade_parsing_and_summary(self):
        grades = run_evals.parse_grades("MUST 1: PASS - ok\nMUST NOT 1: FAIL - bad\nnoise")
        self.assertEqual(grades, [("MUST 1", "PASS"), ("MUST NOT 1", "FAIL")])
        self.assertEqual(run_evals.summarize({1: grades}), (1, 2))

    def test_pipeline_with_fake_agent_and_judge(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = run_evals.main(["1", "--agent-cmd", "cat", "--judge-cmd",
                                 "printf 'MUST 1: PASS - ok\\nMUST NOT 1: PASS - ok\\n'", "--out", tmp])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(tmp) / "1-answer.md").read_text().startswith("Use the skill"))
            self.assertIn("PASS", (Path(tmp) / "1-grading.md").read_text())


if __name__ == "__main__":
    unittest.main()
