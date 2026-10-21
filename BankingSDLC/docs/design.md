# System Design

## Architecture
Browser UI → Flask routes and role checks → SQLite relational database. Werkzeug handles password hashing; Python logging records events.

## ER diagram (Mermaid)
```mermaid
erDiagram
 USERS ||--o{ ACCOUNTS : owns
 USERS ||--o{ LOANS : applies_for
 ACCOUNTS ||--o{ TRANSACTIONS : has
 ACCOUNTS o|--o{ TRANSACTIONS : related_account
 USERS { int id PK; string username UK; string password_hash; string role; string full_name }
 ACCOUNTS { int id PK; int user_id FK; string account_number UK; string account_type; int balance_cents }
 TRANSACTIONS { int id PK; int account_id FK; int related_account_id FK; string tx_type; int amount_cents; string description; datetime created_at }
 LOANS { int id PK; int user_id FK; int amount_cents; string purpose; string status; datetime created_at }
```

## Use cases
Customer: register/sign in, view account, deposit/withdraw/transfer, view history, apply for loan, view loan status.
Administrator: view demo accounts and transactions, approve/reject loan requests.

## Transfer activity
Start → enter accounts and amount → validate source/destination and amount → check available balance → debit source and credit destination → record both sides → commit; otherwise rollback and display error.

## Database schema
- users: unique username, password hash, role, full name.
- accounts: owner foreign key, unique account number, type, integer-cent balance.
- transactions: account and optional related account, type, positive amount, description, timestamp.
- loans: applicant, positive amount, purpose, status, timestamp.

## Design decisions
Money is stored in integer cents to avoid floating-point calculations. SQL is parameterized. Monetary changes use database transactions. This demo does not provide an audit-grade ledger or production-grade concurrency controls.
