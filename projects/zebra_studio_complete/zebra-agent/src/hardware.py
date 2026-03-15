import shutil, os, platform
try:
    import psutil
except Exception:
    psutil = None
def detect_hardware():
    out = {"platform": platform.platform(), "cpu": os.cpu_count(), "disk_free_gb": round(shutil.disk_usage('/').free / (1024**3), 2)}
    if psutil: out["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
    gpu = None
    try:
        import torch
        if torch.cuda.is_available(): gpu = torch.cuda.get_device_name(0)
    except Exception:
        gpu = None
    out["gpu"] = gpu
    return out
