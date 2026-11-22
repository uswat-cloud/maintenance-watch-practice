import csv
from datetime import date
from pathlib import Path
import tempfile
import unittest

from build_report import ROOT, build_report, load_tasks, summarize, upcoming


AS_OF = date(2026, 11, 20)
HEADERS = ["task_id", "application", "activity", "owner", "due_date", "status"]


def task(task_id="TASK-001", due="2026-11-20", status="Open"):
    return dict(zip(HEADERS, [
        task_id, "Atlas Docs", "Certificate renewal", "Ops Team A", date.fromisoformat(due), status,
    ]))


class DateWindowTests(unittest.TestCase):
    def test_includes_today(self):
        self.assertEqual(len(upcoming([task()], AS_OF)), 1)

    def test_includes_day_30(self):
        self.assertEqual(len(upcoming([task(due="2026-12-20")], AS_OF)), 1)

    def test_excludes_day_31(self):
        self.assertEqual(upcoming([task(due="2026-12-21")], AS_OF), [])

    def test_excludes_overdue(self):
        self.assertEqual(upcoming([task(due="2026-11-19")], AS_OF), [])

    def test_excludes_completed(self):
        self.assertEqual(upcoming([task(status="Completed")], AS_OF), [])

    def test_includes_in_progress(self):
        self.assertEqual(len(upcoming([task(status="In progress")], AS_OF)), 1)

    def test_orders_by_due_date(self):
        tasks = [task("LATER", "2026-12-01"), task("TODAY")]
        self.assertEqual([row["task_id"] for row in upcoming(tasks, AS_OF)], ["TODAY", "LATER"])

    def test_summary_partitions_every_record(self):
        tasks = [task("A"), task("B", "2026-11-01"), task("C", "2027-01-01"),
                 task("D", status="Completed")]
        self.assertEqual(summarize(tasks, AS_OF), {
            "total": 4, "completed": 1, "overdue": 1, "due_soon": 1, "later": 1,
        })


class SourceValidationTests(unittest.TestCase):
    def write_csv(self, directory, records, headers=HEADERS):
        path = Path(directory) / "records.csv"
        with path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=headers)
            writer.writeheader()
            writer.writerows(records)
        return path

    def test_rejects_missing_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [], ["task_id"])
            with self.assertRaisesRegex(ValueError, "missing"):
                load_tasks(path)

    def test_rejects_invalid_date(self):
        record = task()
        record["due_date"] = "2026-02-30"
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [record])
            with self.assertRaisesRegex(ValueError, "valid YYYY-MM-DD"):
                load_tasks(path)

    def test_rejects_unknown_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [task(status="Maybe")])
            with self.assertRaisesRegex(ValueError, "unsupported status"):
                load_tasks(path)

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [task(), task()])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_tasks(path)

    def test_rejects_blank_owner(self):
        record = task()
        record["owner"] = " "
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [record])
            with self.assertRaisesRegex(ValueError, "every required field"):
                load_tasks(path)


class OutputTests(unittest.TestCase):
    def test_build_creates_html_and_correct_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            result = build_report([task(), task("DONE", status="Completed")], AS_OF, directory)
            html = (Path(directory) / "index.html").read_text()
            self.assertIn("Maintenance Watch", html)
            self.assertIn("2026-11-20", html)
            with (Path(directory) / "due_soon.csv").open(newline="") as source:
                self.assertEqual([row["task_id"] for row in csv.DictReader(source)], ["TASK-001"])
            self.assertEqual(result["total"], 2)

    def test_html_escapes_source_text(self):
        record = task()
        record["application"] = "<script>alert('test')</script>"
        with tempfile.TemporaryDirectory() as directory:
            build_report([record], AS_OF, directory)
            html = (Path(directory) / "index.html").read_text()
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn("<script>alert('test')</script>", html)

    def test_sample_data_reconciles(self):
        tasks = load_tasks(ROOT / "data" / "maintenance.csv")
        self.assertEqual(len(tasks), 72)
        self.assertEqual(summarize(tasks, AS_OF), {
            "total": 72, "completed": 24, "overdue": 8, "due_soon": 24, "later": 16,
        })


if __name__ == "__main__":
    unittest.main()
