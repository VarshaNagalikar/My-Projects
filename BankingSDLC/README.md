# BankSphere — Banking Management System (SDLC Major Project)

**Educational demo only; not production banking software.** It simulates account operations and does not connect to real banks or move real money.

## Included features
- Customer registration/login; Werkzeug password hashing
- Customer/admin roles
- Automatic demo savings account creation
- Simulated deposits, withdrawals, and transfers with balance checks
- Transaction history
- Loan applications; administrator approval/rejection
- SQLite relational database, foreign keys, constraints, parameterized SQL
- Application logging, error handling, automated smoke tests
- SRS, design/ER diagram, user manual, maintenance notes, test plan in `docs/`

## Run on Windows
Install Python 3.10+. Open PowerShell in this folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flask --app app init-db
python app.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and retry activation. Open http://127.0.0.1:5000.

macOS/Linux: `python3 -m venv .venv`, `source .venv/bin/activate`, then run the pip, Flask, and Python commands above.

## Demo logins
- Administrator: `admin` / `Admin123!`
- Customer: `customer` / `Customer123!`

Public demo credentials are included for local testing. Remove or change seed accounts before any shared deployment.

## Test
```powershell
python -m pytest -q
```
Run the tests and record the actual results in `docs/test-report.md`; do not claim they passed until executed.

## SDLC artifacts
- `docs/requirements.md` — functional/non-functional requirements
- `docs/design.md` — architecture, Mermaid ER diagram, use-case/activity flows, schema
- `docs/user-manual.md` — customer and admin instructions
- `docs/test-report.md` — test cases and results template
- `docs/maintenance.md` — logging, maintenance, deployment notes

## GitHub upload
Upload `app.py`, `requirements.txt`, `.gitignore`, `README.md`, `tests/`, and `docs/`. Do not upload `.venv/`, `banking.db`, `banking.log`, `.env`, secrets, or real customer data.

## Limitations and security
Uses SQLite for easy local execution. Demo transactions are not real bank transactions; loan decisions are a simple status workflow. This has not undergone a security audit and is not suitable for real financial data. Before any public deployment: configure a strong random `BANKING_SECRET_KEY`, use HTTPS and a production WSGI server, add CSRF protection and rate limiting, use a managed database, backups, monitoring, stronger audit controls, and an independent security review. Use synthetic data only.
