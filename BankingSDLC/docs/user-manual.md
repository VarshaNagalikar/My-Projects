# User Manual

## Start
Follow the root README setup. Open http://127.0.0.1:5000.

## Customer
1. Sign in with the demo customer or create an account.
2. Review the account number and balance.
3. Submit a deposit, withdrawal, or transfer with a positive amount. For transfers, enter a different existing destination account number.
4. Open Transaction history.
5. Open Loans, submit an amount and purpose, and check the status later.
6. Sign out.

## Administrator
1. Sign in with the demo admin credentials.
2. Review accounts and open Review loans.
3. Approve or reject pending loan requests.
4. Review transaction history.

## Troubleshooting
- Missing dependencies: activate the virtual environment and run `python -m pip install -r requirements.txt`.
- Initialize tables/demo users: `flask --app app init-db`.
- Keep this app local; never enter real financial data.
