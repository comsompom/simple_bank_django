from locust import HttpUser, between, task


class SimpleBankUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.post(
            "/api/v1/auth/login/",
            json={"email": "sender@example.com", "password": "Passw0rd!234"},
        )

    @task(3)
    def health_like_read(self):
        self.client.get("/api/v1/accounts/balance/")

    @task(1)
    def transactions(self):
        self.client.get("/api/v1/transactions/")
