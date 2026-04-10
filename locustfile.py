from locust import HttpUser, between, task


class MediaHostingUser(HttpUser):
    # Simulate natural user think time while keeping pressure high.
    wait_time = between(0.1, 0.6)

    @task(1)
    def health(self):
        self.client.get("/", name="GET /")

    @task(5)
    def image(self):
        self.client.get("/image", name="GET /image")

    @task(1)
    def nginx_health(self):
        self.client.get("/nginx-health", name="GET /nginx-health")
