import json, shutil, os, platform
try:
    import psutil
except Exception:
    psutil = None

def scan():
    out = {
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "disk_free_gb": round(shutil.disk_usage('/').free / (1024**3), 2),
    }
    if psutil:
        out["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
    return out

if __name__ == "__main__":
    print(json.dumps(scan(), indent=2))
