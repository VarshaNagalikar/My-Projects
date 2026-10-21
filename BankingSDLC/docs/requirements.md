# Software Requirements Specification (SRS)

## Objective
Demonstrate a banking workflow through a local web application while documenting the SDLC. This is a simulation, not a real financial service.

## Actors
- Customer: register, sign in, view own account, perform simulated transactions, view history, apply for loans and check status.
- Administrator: view demo accounts and transaction history; approve/reject pending loans.

## Functional requirements
1. Customers can register with a unique username.
2. Passwords are stored as hashes, not plaintext.
3. Customers can sign in and sign out.
4. Customers can view only their own accounts and loan applications.
5. Customers can deposit, withdraw, and transfer simulated funds.
6. Withdrawals/transfers cannot create a negative balance.
7. Transactions are recorded in history.
8. Customers can submit loan applications.
9. Administrators can approve/reject pending loans.
10. The app logs significant events and unexpected failures.

## Non-functional requirements
- Security: password hashing, parameterized SQL, role checks, HTTP-only session cookies.
- Integrity: integer cents, relational constraints, transaction rollback.
- Usability: responsive layout and clear messages.
- Maintainability: documented setup and automated tests.
- Privacy: use synthetic data only.
- Portability: Python/Flask/SQLite for local execution.

## Constraints
SQLite is selected for simple setup. A production implementation needs further controls including CSRF protection, rate limiting, HTTPS, secure secret management, backups, monitoring, and independent security review.
