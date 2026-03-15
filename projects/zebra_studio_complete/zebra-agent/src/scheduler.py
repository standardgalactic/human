def score_task(task, hw, interests):
    score = task.get("assembly_weight", 1.0)
    if task.get("projection") == "diagrammatic_structure" and hw.get("cpu", 1) >= 4: score += 0.5
    if task.get("projection") == "narrative_film" and hw.get("gpu"): score += 0.5
    topic = "programming"
    title = task.get("title","").lower()
    if "diagram" in title: topic = "math"
    if "scene" in title: topic = "art"
    score *= max(0.1, interests.get(topic, 0.1))
    return score
def choose_tasks(tasks, hw, interests, n=5):
    return sorted(tasks, key=lambda t: score_task(t, hw, interests), reverse=True)[:n]
