# Maintenance and Deployment

## Logs
`banking.log` records sign-ins, registration, transaction/loan events, and exceptions. It should never contain passwords. Restrict access and rotate logs for a hosted deployment.

## Maintenance
- Update Python/dependencies and rerun tests.
- Review errors and repeated failed login attempts.
- Back up the database before schema changes and test restoration.
- Remove demo credentials before shared deployment.
- Keep secrets out of source control.
- Add migration tooling when schema changes become frequent.

## Deployment
Use localhost for the college demo. For hosting, use a production WSGI server, HTTPS, a managed database, environment secrets, backups, monitoring, network restrictions, CSRF protection, rate limiting, and a security review. Do not use Flask's development server in production.
