
def score_task(task, hw, interests):

    score = task.get("assembly_weight",1)

    if task.get("projection") == "diagrammatic" and hw["cpu"] >= 4:
        score += 0.5

    if task.get("projection") == "narrative" and hw["gpu"]:
        score += 0.5

    for k,v in interests.items():
        if k in task["title"].lower():
            score += v * 0.1

    return score


def choose_tasks(tasks, hw, interests, n=3):

    ranked = sorted(
        tasks,
        key=lambda t: score_task(t,hw,interests),
        reverse=True
    )

    return ranked[:n]
