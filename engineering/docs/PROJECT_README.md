[Project homepage](../../README.md)

# Project Structure

```text
repository/
├── .github/workflows/          # Automation
├── engineering/                # Engineering implementation and data
│   ├── assets/                 # Paper resources
│   ├── backups/                # Generated backups
│   ├── build/                  # Local build output
│   ├── config/                 # Runtime and taxonomy configuration
│   ├── dist/                   # Packaged application output
│   ├── docs/                   # Engineering documentation
│   ├── figures_temp/           # Temporary figures
│   ├── scripts/                # CI and maintenance scripts
│   ├── src/                    # Application source
│   ├── tests/                  # Automated tests
│   ├── paper_database_for_survey.csv
│   └── paper_database_complete_list.csv
├── figures/                    # Legacy-compatible figures
├── COMPLETE_LIST.md            # Compact complete paper list
├── README.md                   # Main curated paper list
├── submit.py                   # Submission GUI entry point
├── submit_template.json
├── submit_template.xlsx
└── pyproject.toml
```

Run commands from the repository root. See [engineering/README.md](../README.md) for common entry points.
