"""Make ready-to-post still images from white-box reels (for manual posting).

For every N.mp4 in a folder it writes:
  N_post.png   1080x1350 (4:5)  - Instagram feed photo post
  N_story.png  1080x1920 (9:16) - Story / reel cover upload
Both are the reel's final frame, with the full joke visible.

Usage: python3 make_stills.py reels/YYYY-MM-DD
"""
import glob, os, subprocess, sys
from PIL import Image

folder = sys.argv[1]
for mp4 in sorted(glob.glob(os.path.join(folder, "*.mp4"))):
    base = mp4[:-4]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", mp4]))
    story = base + "_story.png"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0, dur - 0.5):.2f}", "-i", mp4,
                    "-frames:v", "1", story], check=True)
    im = Image.open(story).convert("RGB")
    W, H = im.size
    # 4:5 feed crop centred on the white box (box is vertically centred in the reel)
    ph = int(W * 5 / 4)
    top = (H - ph) // 2
    im.crop((0, top, W, top + ph)).save(base + "_post.png", optimize=True)
    im.save(story, optimize=True)
    print(base + "_post.png", base + "_story.png")
