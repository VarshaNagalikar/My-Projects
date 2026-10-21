# BugPilot — Bug Tracking System

A runnable Flask + Bootstrap + SQLite starter for the Software Engineering minor project. It includes authentication, three roles, bug CRUD, search/filter, assignment and status notifications, comments, status history, a dashboard, sample data, and a role-aware workflow.

## Requirements

- Python 3.10+
- Internet connection for the Bootstrap CDN and Google Fonts (the app itself runs locally; styling falls back if fonts are unavailable)

## Run on Windows (PowerShell)

```powershell
cd BugPilot
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flask --app app seed
python app.py
```

If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again, or run `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe -m flask --app app seed`.

## Run on macOS / Linux

```bash
cd BugPilot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
flask --app app seed
python app.py
```

Open http://127.0.0.1:5000.

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Tester | `tester` | `Tester123!` |
| Developer | `developer` | `Developer123!` |
| Project Manager | `manager` | `Manager123!` |

These are local demonstration credentials only. Change them before any deployment. The `seed` command intentionally skips seeding if a user already exists. To reset the demo database, stop the server, delete `bugpilot.db`, then run `flask --app app seed` again.

## Features in this starter

- Login/logout with hashed passwords and Flask-Login session handling.
- Roles: Tester, Developer, Project Manager; the manager can view team members and delete bugs.
- Create, read, update and delete bug reports (delete is manager-only).
- Bug key format `BUG-0001`, 11 selectable lifecycle statuses (New, Open, Assigned, In Progress, On Hold, Fixed, Ready for Testing, In Testing, Reopened, Verified, Closed), priority, severity, reporter, assignee, environment, reproduction steps, expected/actual result.
- Search by issue ID, title, and description; filters for status, priority and assignee.
- Status history and in-app notifications for assignment, comments and status changes.
- Comments, dashboard summary cards, status breakdown and seeded sample defects.
- Role rules prevent developers from verifying/closing bugs and testers from marking a bug Fixed.

## Assignment requirement coverage

1. Objective: described above and in the dashboard.
2. Roles: Tester, Developer, Project Manager.
3. Database schema: User, Bug, Comment, StatusHistory, Notification.
4. Platform: Flask web app.
5. CRUD: bug create/view/edit/delete routes.
6. Search/filter: `/bugs` page.
7. Notifications/status updates: `/notifications` and status history.
8. Sample data/testing: `flask --app app seed` creates demo users and five sample bugs.
9. Documentation: this README and in-app workflow guidance; add screenshots and a final report for submission.
10. Deployment: local run instructions included; cloud deployment can be added after testing.

## Important limitations before production

This is a **first runnable project version**, not a production-hardened Jira replacement. Before exposing it to the internet, add CSRF protection (for example Flask-WTF), rate limiting, email verification/password reset, secure production secret configuration, HTTPS, stronger permission rules, attachment scanning/storage, pagination, automated tests, backups, and a production WSGI server. The development server and default secret are for local demos only. Bootstrap and fonts load from CDNs.

## Suggested next steps

1. Run through each demo account and test all assignment requirements.
2. Add pytest tests for authentication, CRUD, filters, role restrictions and notifications.
3. Add screenshot/file attachments and projects.
4. Prepare project report, ER diagram, test cases, screenshots and demo script.
