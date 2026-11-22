# Maintenance Watch

A small Python application that builds an application-maintenance report from fictional records.

## Data and report

The CSV contains 72 made-up activities across eight fictional applications. It covers certificate renewals, password rotations, patching, vulnerabilities, DR checks and vendor reviews.

For the reporting date **2026-11-20**, the expected totals are:

| Metric | Count |
| --- | ---: |
| All tasks | 72 |
| Completed | 24 |
| Incomplete and overdue | 8 |
| Incomplete and due today through day 30 | 24 |
| Incomplete and due later | 16 |

The upcoming window includes both **2026-11-20** and **2026-12-20**. Completed tasks and overdue tasks do not appear in the upcoming CSV.

## Commands

Install the report's template dependency:

```bash
python -m pip install -r requirements.txt
```

Run the 16 tests:

```bash
python -m unittest discover -s tests -v
```

Build the static report and upcoming-work CSV:

```bash
python build_report.py --as-of 2026-11-20 --output site
```

The output is `site/index.html` and `site/due_soon.csv`. The report has no server-side service or login.

## Repository contents

| Path | Purpose |
| --- | --- |
| `build_report.py` | Validate data, calculate metrics and generate the report |
| `requirements.txt` | Pin the Jinja template dependency |
| `data/maintenance.csv` | Fictional source data |
| `templates/report.html` | Static report layout |
| `tests/test_report.py` | Boundary, data-validation and output tests |

This starter has no GitHub Actions workflow. Its tests and report can be used to configure and verify a build-and-deployment pipeline.
