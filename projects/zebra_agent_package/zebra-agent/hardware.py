
import psutil

def detect_hardware():
    cpu = psutil.cpu_count(logical=True)
    ram = psutil.virtual_memory().total / (1024**3)
    disk = psutil.disk_usage("/").free / (1024**3)

    gpu = None
    try:
        import torch
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
    except Exception:
        pass

    return {
        "cpu": cpu,
        "ram_gb": round(ram,2),
        "disk_free_gb": round(disk,2),
        "gpu": gpu
    }
