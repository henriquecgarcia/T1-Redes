import csv
import json
import math
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze


class AnalysisTests(unittest.TestCase):
	def test_ci_uses_rounds(self):
		mean, lo, hi = analyze.avg_ci([1, 3])
		self.assertEqual(mean, 2)
		self.assertAlmostEqual(hi - mean, 12.7062047364, places=7)
		self.assertAlmostEqual(mean - lo, hi - mean)

	def test_one_round_no_ci(self):
		mean, lo, hi = analyze.avg_ci([2])
		self.assertEqual(mean, 2)
		self.assertTrue(math.isnan(lo) and math.isnan(hi))

	def test_complete_committed_attempt_only(self):
		old = analyze.ROOT
		try:
			with tempfile.TemporaryDirectory() as d:
				analyze.ROOT = Path(d)
				(Path(d) / "evidencias").mkdir()
				with (Path(d) / "resultados_brutos.csv").open("w") as f:
					w = csv.DictWriter(f, ["round_id", "attempt", "clients", "client_id", "phase"])
					w.writeheader()
					for attempt, ids in [("old", [1, 2]), ("new", [1, 2]), ("partial", [1])]:
						for i in ids:
							w.writerow(
								dict(
									round_id="r1" if attempt != "partial" else "r2",
									attempt=attempt,
									clients=2,
									client_id=i,
									phase="main",
								)
							)
				(Path(d) / "evidencias/rodadas_concluidas.jsonl").write_text(
					json.dumps(dict(round_id="r1", attempt="new"))
					+ "\n"
					+ json.dumps(dict(round_id="r2", attempt="partial"))
					+ "\n"
				)
				rows, excluded = analyze.selected_rows()
				self.assertEqual(len(rows), 2)
				self.assertEqual(len(excluded), 3)
				self.assertTrue(all(r["attempt"] == "new" for r in rows))
		finally:
			analyze.ROOT = old


if __name__ == "__main__":
	unittest.main(verbosity=2)
