import subprocess

def transcode(input_path: str, output_path: str):
    subprocess.run(["ffmpeg", "-y", "-i", input_path, "-c:v", "libx264", "-preset", "fast", output_path], check=False)
