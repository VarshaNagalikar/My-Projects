# Test Plan and Test Report

## Automated tests
Run `python -m pytest -q`. Included smoke tests cover home page, customer login, incorrect password rejection, loan submission, and administrator loan review. Record the actual output below after running; do not claim pass results without execution.

## Manual test cases
| ID | Scenario | Expected result |
|---|---|---|
| TC-01 | Register new customer | Unique customer and zero-balance account created |
| TC-02 | Duplicate username | Friendly error; no duplicate user |
| TC-03 | Wrong password | Login rejected |
| TC-04 | Deposit positive amount | Balance and history increase |
| TC-05 | Withdraw within balance | Balance decreases and history records transaction |
| TC-06 | Withdraw over balance | Error; balance unchanged |
| TC-07 | Transfer to valid account | Both balances update; both sides recorded |
| TC-08 | Invalid transfer | Error; balances unchanged |
| TC-09 | Apply for loan | Loan is Pending |
| TC-10 | Admin loan decision | Status changes to Approved or Rejected |
| TC-11 | Customer attempts admin route | Access denied/redirected |
| TC-12 | Invalid amount | Error; no balance change |

## Results to fill after testing
- Date and environment:
- Automated tests passed/failed:
- Manual test IDs executed:
- Defects found and fixes:
- UAT acceptance/sign-off:
