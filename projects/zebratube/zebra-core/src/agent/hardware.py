#!/usr/bin/env python3
"""
agent/hardware.py — hardware capability detection

Measures the local machine's computational resources and available tools,
then returns a typed CapabilityProfile. This is the first sensing phase
of the Zebra agent.

No external dependencies required for the core measurements.
Optional: pynvml (Nvidia), pyaudio (microphone), pillow (image).
"""

import json
import multiprocessing
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional


# ── GPU detection ─────────────────────────────────────────────────────────────

@dataclass
class GPUInfo:
    name:      str
    vram_gb:   float
    backend:   str   # "cuda" | "metal" | "opencl" | "none"


def _detect_nvidia() -> list[GPUInfo]:
    try:
        import pynvml
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        gpus = []
        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            mem  = pynvml.nvmlDeviceGetMemoryInfo(h)
            gpus.append(GPUInfo(
                name=name if isinstance(name, str) else name.decode(),
                vram_gb=round(mem.total / 1e9, 1),
                backend="cuda",
            ))
        return gpus
    except Exception:
        return []


def _detect_apple_silicon() -> list[GPUInfo]:
    if platform.system() != "Darwin":
        return []
    try:
        out = subprocess.run(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        data = json.loads(out)
        cards = data.get("SPDisplaysDataType", [])
        result = []
        for card in cards:
            name = card.get("sppci_model", "Apple GPU")
            # Apple unified memory; report system RAM as shared VRAM
            result.append(GPUInfo(name=name, vram_gb=0.0, backend="metal"))
        return result
    except Exception:
        return []


def detect_gpus() -> list[GPUInfo]:
    gpus = _detect_nvidia()
    if not gpus:
        gpus = _detect_apple_silicon()
    return gpus


# ── RAM / CPU / Disk ──────────────────────────────────────────────────────────

def detect_ram_gb() -> float:
    try:
        import psutil
        return round(psutil.virtual_memory().total / 1e9, 1)
    except ImportError:
        pass
    # Fallback: /proc/meminfo on Linux
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return round(kb / 1e6, 1)
    except Exception:
        pass
    return 0.0


def detect_disk_free_gb(path: str = "/") -> float:
    try:
        stat = shutil.disk_usage(path)
        return round(stat.free / 1e9, 1)
    except Exception:
        return 0.0


def detect_cpu_cores() -> int:
    return multiprocessing.cpu_count()


# ── Tool detection ────────────────────────────────────────────────────────────

TOOL_CHECKS: dict[str, list[str]] = {
    "ffmpeg":     ["ffmpeg",   "-version"],
    "blender":    ["blender",  "--version"],
    "latex":      ["pdflatex", "--version"],
    "lualatex":   ["lualatex", "--version"],
    "inkscape":   ["inkscape", "--version"],
    "imagemagick":["convert",  "--version"],
    "ollama":     ["ollama",   "--version"],
    "git":        ["git",      "--version"],
    "python":     [sys.executable, "--version"],
    "node":       ["node",     "--version"],
}

PYTHON_PKG_CHECKS = [
    "matplotlib", "networkx", "numpy", "scipy",
    "sentence_transformers", "sklearn", "torch",
    "PIL", "cv2", "librosa", "pretty_midi",
    "requests", "fastapi", "celery",
]


def detect_tools() -> dict[str, bool]:
    found: dict[str, bool] = {}
    for tool, cmd in TOOL_CHECKS.items():
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=5)
            found[tool] = r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            found[tool] = False
    return found


def detect_python_packages() -> dict[str, bool]:
    found: dict[str, bool] = {}
    for pkg in PYTHON_PKG_CHECKS:
        try:
            __import__(pkg)
            found[pkg] = True
        except ImportError:
            found[pkg] = False
    return found


# ── Input device detection ────────────────────────────────────────────────────

def detect_microphone() -> bool:
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        count = p.get_device_count()
        for i in range(count):
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                p.terminate()
                return True
        p.terminate()
        return False
    except Exception:
        pass
    # Fallback: check /dev/snd on Linux
    try:
        import glob
        return len(glob.glob("/dev/snd/pcmC*D*c")) > 0
    except Exception:
        return False


def detect_camera() -> bool:
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        opened = cap.isOpened()
        cap.release()
        return opened
    except Exception:
        pass
    # Fallback: check /dev/video* on Linux
    try:
        import glob
        return len(glob.glob("/dev/video*")) > 0
    except Exception:
        return False


def detect_display() -> bool:
    """Check whether a display is available for GUI rendering."""
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return True
    if platform.system() == "Darwin":
        return True
    if platform.system() == "Windows":
        return True
    return False


# ── Capability derivation ─────────────────────────────────────────────────────

@dataclass
class CapabilityProfile:
    # Hardware
    cpu_cores:    int
    ram_gb:       float
    disk_free_gb: float
    gpus:         list[GPUInfo]
    has_mic:      bool
    has_camera:   bool
    has_display:  bool
    platform:     str

    # Tools
    tools:            dict[str, bool]
    python_packages:  dict[str, bool]

    # Derived capability tags
    capabilities: list[str] = field(default_factory=list)

    def total_vram_gb(self) -> float:
        return sum(g.vram_gb for g in self.gpus)

    def has_gpu(self) -> bool:
        return len(self.gpus) > 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_vram_gb"] = self.total_vram_gb()
        d["has_gpu"] = self.has_gpu()
        return d

    def to_api_payload(self) -> dict:
        """Minimal payload sent to ZebraTube server — no raw file paths."""
        return {
            "cpu_cores":     self.cpu_cores,
            "ram_gb":        self.ram_gb,
            "disk_free_gb":  self.disk_free_gb,
            "has_gpu":       self.has_gpu(),
            "gpu_names":     [g.name for g in self.gpus],
            "total_vram_gb": self.total_vram_gb(),
            "gpu_backend":   self.gpus[0].backend if self.gpus else "none",
            "has_mic":       self.has_mic,
            "has_camera":    self.has_camera,
            "has_display":   self.has_display,
            "platform":      self.platform,
            "capabilities":  self.capabilities,
            "tools":         {k: v for k, v in self.tools.items() if v},
        }


def _derive_capabilities(profile: CapabilityProfile) -> list[str]:
    caps: list[str] = []
    t = profile.tools
    p = profile.python_packages

    # Video
    if t.get("ffmpeg"):
        caps.append("video_processing")
    if t.get("ffmpeg") and profile.has_gpu():
        caps.append("video_rendering_gpu")
    if t.get("ffmpeg") and profile.ram_gb >= 8:
        caps.append("video_rendering_cpu")

    # 3D / animation
    if t.get("blender"):
        caps.append("3d_animation")
        if profile.has_gpu():
            caps.append("gpu_rendering")

    # Diagram / image
    if p.get("matplotlib") and p.get("networkx"):
        caps.append("diagram_generation")
    if t.get("inkscape") or t.get("imagemagick"):
        caps.append("vector_graphics")

    # LLM inference
    if t.get("ollama"):
        caps.append("llm_inference")
    if p.get("torch") and profile.has_gpu():
        caps.append("llm_inference_gpu")

    # LaTeX / mathematical
    if t.get("latex") or t.get("lualatex"):
        caps.append("latex_typesetting")
    if p.get("matplotlib") and (t.get("latex") or t.get("lualatex")):
        caps.append("mathematical_diagram")

    # Audio
    if profile.has_mic and t.get("ffmpeg"):
        caps.append("narration")
    if p.get("librosa") or p.get("pretty_midi"):
        caps.append("audio_processing")

    # Screen recording
    if profile.has_display and t.get("ffmpeg"):
        caps.append("screen_recording")

    # Camera capture
    if profile.has_camera and t.get("ffmpeg"):
        caps.append("video_capture")

    # Embeddings / semantic
    if p.get("sentence_transformers"):
        caps.append("local_embeddings")

    # Generic compute
    if profile.ram_gb >= 32 and profile.cpu_cores >= 8:
        caps.append("heavy_compute")
    elif profile.ram_gb >= 8:
        caps.append("standard_compute")
    else:
        caps.append("light_compute")

    return sorted(set(caps))


# ── Main entry point ──────────────────────────────────────────────────────────

def detect() -> CapabilityProfile:
    """Run full hardware detection and return a CapabilityProfile."""
    gpus    = detect_gpus()
    tools   = detect_tools()
    pkgs    = detect_python_packages()

    profile = CapabilityProfile(
        cpu_cores    = detect_cpu_cores(),
        ram_gb       = detect_ram_gb(),
        disk_free_gb = detect_disk_free_gb(),
        gpus         = gpus,
        has_mic      = detect_microphone(),
        has_camera   = detect_camera(),
        has_display  = detect_display(),
        platform     = platform.system().lower(),
        tools        = tools,
        python_packages = pkgs,
        capabilities = [],
    )
    profile.capabilities = _derive_capabilities(profile)
    return profile


if __name__ == "__main__":
    p = detect()
    print(json.dumps(p.to_dict(), indent=2))
