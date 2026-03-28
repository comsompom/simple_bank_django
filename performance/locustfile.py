import uuid

from locust import HttpUser, between, task


class SimpleBankUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        email = f"load-{uuid.uuid4().hex[:10]}@example.com"
        password = "Passw0rd!234"

        register_response = self.client.post(
            "/api/v1/auth/register/",
            json={
                "email": email,
                "full_name": "Load Test User",
                "password": password,
            },
            name="auth_register",
        )
        if register_response.status_code != 201:
            register_response.failure(f"register failed: {register_response.text}")
            return

        login_response = self.client.post(
            "/api/v1/auth/login/",
            json={"email": email, "password": password},
            name="auth_login",
        )
        if login_response.status_code != 200:
            login_response.failure(f"login failed: {login_response.text}")
            return

        token = login_response.json()["access"]
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(3)
    def balance(self):
        self.client.get("/api/v1/accounts/balance/", name="account_balance")

    @task(2)
    def account_profile(self):
        self.client.get("/api/v1/accounts/me/", name="account_me")

    @task(2)
    def transactions(self):
        self.client.get("/api/v1/transactions/", name="transactions_list")

    @task(1)
    def fee_estimate(self):
        self.client.get("/api/v1/transfers/fees/estimate/?amount=125.00", name="transfer_fee_estimate")

    @task(1)
    def me_profile(self):
        self.client.get("/api/v1/auth/me/", name="auth_me")

    @task(1)
    def qr_generate(self):
        self.client.post(
            "/api/v1/qr/generate/",
            json={"amount": "10.00", "note": "Load test"},
            name="qr_generate",
        )
