from pathlib import Path
import subprocess
def render_concat(paths, output_path):
    tmp = Path("segments.txt")
    tmp.write_text("\n".join([f"file '{p}'" for p in paths]), encoding="utf-8")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(tmp),"-c","copy",output_path], check=False)
