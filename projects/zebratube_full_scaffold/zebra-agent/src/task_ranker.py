def rank_task(task, hw_profile, interest_profile):
    scarcity = 1.0 / (1.0 + task.get("submission_count", 0))
    assembly_weight = task.get("assembly_weight", 1.0)
    topic = task.get("topic", "programming")
    interest = interest_profile.get(topic, 0.1)
    capability = 1.0
    if task.get("output_format") == "video" and hw_profile.get("disk_free_gb", 0) < 5:
        capability = 0.2
    return capability * scarcity * assembly_weight * max(0.1, interest)
