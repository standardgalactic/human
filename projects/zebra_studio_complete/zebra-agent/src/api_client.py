import requests
class ZebraAPI:
    def __init__(self, url, user): self.url, self.user = url, user
    def get_tasks(self): return requests.get(f"{self.url}/tasks").json()
    def claim_task(self, task_id): return requests.post(f"{self.url}/claims", json={"task_id": task_id, "user_id": self.user}).json()
