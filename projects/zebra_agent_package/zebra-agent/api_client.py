
import requests

class ZebraAPI:

    def __init__(self, url, user):
        self.url = url
        self.user = user

    def get_tasks(self):
        r = requests.get(f"{self.url}/tasks")
        return r.json()

    def claim_task(self, task_id):
        payload = {"task_id": task_id, "user_id": self.user}
        r = requests.post(f"{self.url}/claims", json=payload)
        return r.json()
