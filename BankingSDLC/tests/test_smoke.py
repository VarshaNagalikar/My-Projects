import os, tempfile
import pytest
import app as bank

@pytest.fixture()
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd)
    monkeypatch.setattr(bank, "DB_PATH", path)
    bank.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    bank.init_db()
    with bank.app.test_client() as c: yield c
    os.unlink(path)

def signin(c, username, password):
    return c.post("/login", data={"username":username,"password":password}, follow_redirects=True)

def test_home(client):
    assert client.get("/").status_code == 200

def test_customer_login(client):
    r=signin(client,"customer","Customer123!")
    assert r.status_code == 200 and b"1000000001" in r.data

def test_bad_password(client):
    r=signin(client,"customer","wrong")
    assert b"Invalid username or password" in r.data

def test_customer_applies_for_loan(client):
    signin(client,"customer","Customer123!")
    r=client.post("/loans",data={"amount":"5000","purpose":"Education costs"},follow_redirects=True)
    assert b"Loan application submitted" in r.data

def test_admin_can_review_loan(client):
    signin(client,"customer","Customer123!")
    client.post("/loans",data={"amount":"5000","purpose":"Education costs"},follow_redirects=True)
    client.post("/logout",follow_redirects=True)
    signin(client,"admin","Admin123!")
    assert b"Education costs" in client.get("/loans").data
