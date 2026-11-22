"""Build a static report from fictional application-maintenance records."""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parent
FIELDS = {"task_id", "application", "activity", "owner", "due_date", "status"}
STATUSES = {"Open", "In progress", "Completed"}


def load_tasks(path):
    """Read and validate records; reject incomplete or ambiguous source data."""
    tasks = []
    seen = set()
    with Path(path).open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not FIELDS.issubset(set(reader.fieldnames or [])):
            raise ValueError("The CSV is missing one or more required columns.")
        for line, row in enumerate(reader, start=2):
            task = {field: (row.get(field) or "").strip() for field in FIELDS}
            if not all(task.values()):
                raise ValueError(f"Line {line}: every required field needs a value.")
            if task["task_id"] in seen:
                raise ValueError(f"Line {line}: duplicate task ID {task['task_id']}.")
            if task["status"] not in STATUSES:
                raise ValueError(f"Line {line}: unsupported status {task['status']}.")
            try:
                task["due_date"] = date.fromisoformat(task["due_date"])
            except ValueError as error:
                raise ValueError(f"Line {line}: use a valid YYYY-MM-DD due date.") from error
            tasks.append(task)
            seen.add(task["task_id"])
    return tasks


def summarize(tasks, as_of):
    """Group tasks against a supplied date so results remain reproducible."""
    result = {"total": len(tasks), "completed": 0, "overdue": 0, "due_soon": 0, "later": 0}
    end = as_of + timedelta(days=30)
    for task in tasks:
        if task["status"] == "Completed":
            result["completed"] += 1
        elif task["due_date"] < as_of:
            result["overdue"] += 1
        elif task["due_date"] <= end:
            result["due_soon"] += 1
        else:
            result["later"] += 1
    return result


def upcoming(tasks, as_of):
    """Return incomplete work due today through day 30, including both ends."""
    end = as_of + timedelta(days=30)
    return sorted(
        (task for task in tasks
         if task["status"] != "Completed" and as_of <= task["due_date"] <= end),
        key=lambda task: (task["due_date"], task["task_id"]),
    )


def build_report(tasks, as_of, output_dir):
    environment = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    template = environment.get_template("report.html")
    summary = summarize(tasks, as_of)
    html = template.render(
        tasks=sorted(tasks, key=lambda task: (task["due_date"], task["task_id"])),
        summary=summary,
        as_of=as_of,
        end=as_of + timedelta(days=30),
        applications=sorted({task["application"] for task in tasks}),
    )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / ".nojekyll").touch()
    with (output / "due_soon.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=[
            "task_id", "application", "activity", "owner", "due_date", "status",
        ])
        writer.writeheader()
        writer.writerows(upcoming(tasks, as_of))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "maintenance.csv")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    try:
        summary = build_report(load_tasks(args.data), args.as_of, args.output)
    except ValueError as error:
        parser.exit(1, f"Invalid maintenance data: {error}\n")
    print(f"Report written to {args.output / 'index.html'}")
    print(" | ".join(f"{key}: {value}" for key, value in summary.items()))


if __name__ == "__main__":
    main()
