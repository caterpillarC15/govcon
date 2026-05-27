#!/usr/bin/env python3
"""
Michaela video stitching pipeline with AI frame interpolation.
1. Takes ordered list of clips
2. Extracts last frame of clip N and first frame of clip N+1
3. Generates interpolated transition frames via fal.ai RIFE
4. Stitches with ffmpeg + audio crossfade
"""

import requests
import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

FAL_KEY = "33f25807-23a4-435e-b233-214674f73423:b2442e687be8276e48b32530820a3bb8"
FAL_HEADERS = {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}
WORK_DIR = Path("/root/govcon/stitch_work")
CLIPS_DIR = Path("/root/govcon/clips")
OUTPUT = Path("/root/govcon/michaela-stitched.mp4")

# Order matters — this is the narrative flow
CLIP_ORDER = [
    "warm-nod",        # She greets you
    "over-shoulder",   # Someone called her name
    "playful-smirk",   # She knows something
    "confident-stand"  # Ready to work
]

def run(cmd, **kwargs):
    """Run shell command, print output, raise on failure."""
    print(f"  $ {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr[:500]}")
        raise RuntimeError(f"Command failed: {cmd[:100]}")
    return result.stdout.strip()

def extract_frame(clip_path, timestamp, output_path):
    """Extract a single frame at timestamp from video."""
    output_path = str(output_path)
    clip_path = str(clip_path)
    if timestamp == "end":
        # Get duration then extract last frame
        dur_out = run(f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{clip_path}'")
        duration = float(dur_out.strip())
        timestamp = max(0, duration - 0.1)
    
    run(f"ffmpeg -y -ss {timestamp} -i '{clip_path}' -vframes 1 -q:v 2 '{output_path}'")
    return output_path

def upload_frame(frame_path):
    """Upload frame to fal storage, return public URL."""
    frame_path = Path(frame_path)
    
    # Read as base64 for data URL
    import base64
    with open(frame_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    
    return f"data:image/png;base64,{b64}"

def interpolate_frames(start_url, end_url, num_frames=8):
    """Use fal.ai frame interpolation to generate transition frames."""
    payload = {
        "image_url": start_url,
        "image_url_2": end_url,
        "num_frames": num_frames
    }
    
    print(f"  Requesting {num_frames} interpolated frames...")
    r = requests.post("https://queue.fal.run/fal-ai/frame-interpolation", 
                      headers=FAL_HEADERS, json=payload, timeout=30)
    
    if r.status_code != 200:
        print(f"  Frame interpolation failed: {r.status_code} {r.text[:300]}")
        return None
    
    resp = r.json()
    request_id = resp["request_id"]
    status_url = resp["status_url"]
    
    # Poll until complete
    import time
    for _ in range(60):
        sr = requests.get(status_url, headers=FAL_HEADERS, timeout=10)
        status = sr.json()
        
        if status.get("status") == "COMPLETED":
            result = status.get("result", {})
            frames = result.get("frames") or result.get("images") or []
            if isinstance(result, dict) and "video" in result:
                video_url = result["video"].get("url")
                if video_url:
                    out = WORK_DIR / f"transition_{request_id[:8]}.mp4"
                    vr = requests.get(video_url, timeout=60)
                    with open(out, 'wb') as f:
                        f.write(vr.content)
                    print(f"  ✓ Transition video: {out} ({len(vr.content)/1024:.0f}KB)")
                    return str(out)
            
            # If frames returned as URLs, download them
            if frames:
                frame_paths = []
                for i, f in enumerate(frames):
                    if isinstance(f, dict):
                        url = f.get("url")
                    else:
                        url = f
                    if url:
                        fp = WORK_DIR / f"frame_{request_id[:8]}_{i:03d}.png"
                        fr = requests.get(url, timeout=30)
                        with open(fp, 'wb') as fh:
                            fh.write(fr.content)
                        frame_paths.append(str(fp))
                print(f"  ✓ {len(frame_paths)} transition frames downloaded")
                return frame_paths
            
            print(f"  ⚠ COMPLETED but unexpected result format: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            return None
        
        elif status.get("status") in ("FAILED", "CANCELLED"):
            print(f"  ✗ Interpolation failed: {status.get('status')}")
            return None
        
        time.sleep(2)
    
    print("  ⏱ Timed out waiting for interpolation")
    return None

def frames_to_video(frame_paths, output_path, fps=24):
    """Convert sequence of frame images to video using ffmpeg."""
    if not frame_paths:
        return None
    
    output_path = str(output_path)
    
    if len(frame_paths) == 1 and frame_paths[0].endswith('.mp4'):
        # Already a video from interpolation
        return frame_paths[0]
    
    # Write concat file
    concat_file = WORK_DIR / "frames_concat.txt"
    with open(concat_file, 'w') as f:
        for fp in frame_paths:
            f.write(f"file '{fp}'\n")
            f.write(f"duration {1/fps}\n")
        # Last frame needs duration too
        f.write(f"file '{frame_paths[-1]}'\n")
    
    run(f"ffmpeg -y -f concat -safe 0 -i '{concat_file}' -vsync vfr -pix_fmt yuv420p '{output_path}'")
    return str(output_path)

def main():
    print("=" * 60)
    print("Michaela Video Stitching Pipeline")
    print("=" * 60)
    
    # Clean work dir
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True)
    
    # Step 1: Find clips
    clips = {}
    for label in CLIP_ORDER:
        path = CLIPS_DIR / f"{label}.mp4"
        if path.exists():
            clips[label] = path
            size_mb = path.stat().st_size / (1024*1024)
            print(f"  Found: {label} ({size_mb:.1f}MB)")
        else:
            print(f"  ✗ Missing: {label}")
    
    if not clips:
        print("\nNo clips found! Run Veo3 generation first.")
        sys.exit(1)
    
    # Renumber found clips
    ordered = [label for label in CLIP_ORDER if label in clips]
    
    if len(ordered) < 2:
        print(f"\nOnly {len(ordered)} clip(s) — nothing to stitch. Copying as output.")
        shutil.copy(str(clips[ordered[0]]), str(OUTPUT))
        return
    
    print(f"\nStitching {len(ordered)} clips with AI interpolation...\n")
    
    # Step 2: Extract transition frames and generate interpolations
    transition_videos = []
    segment_paths = []
    
    for i in range(len(ordered) - 1):
        clip_a = clips[ordered[i]]
        clip_b = clips[ordered[i + 1]]
        
        print(f"Transition {i+1}: {ordered[i]} → {ordered[i+1]}")
        
        # Extract last frame of clip A
        last_frame = WORK_DIR / f"last_{ordered[i]}.png"
        extract_frame(clip_a, "end", last_frame)
        
        # Extract first frame of clip B
        first_frame = WORK_DIR / f"first_{ordered[i+1]}.png"
        extract_frame(clip_b, 0.1, first_frame)
        
        # Upload both frames
        last_url = upload_frame(last_frame)
        first_url = upload_frame(first_frame)
        
        # Generate interpolated transition
        transition = interpolate_frames(last_url, first_url, num_frames=8)
        
        if transition:
            if isinstance(transition, list):
                trans_video = frames_to_video(transition, WORK_DIR / f"trans_{i}.mp4", fps=24)
                transition_videos.append(trans_video)
            else:
                transition_videos.append(transition)
        else:
            print(f"  ⚠ No transition for {ordered[i]} → {ordered[i+1]}, using hard cut")
            transition_videos.append(None)
        
        print()
    
    # Step 3: Build ffmpeg concat file with transitions
    concat_file = WORK_DIR / "final_concat.txt"
    with open(concat_file, 'w') as f:
        for i, label in enumerate(ordered):
            # Add clip (trimmed if there's a transition after)
            clip_path = clips[label]
            if i < len(ordered) - 1 and transition_videos[i]:
                # Trim last 0.3s off clip to transition
                dur_out = run(f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{clip_path}'")
                duration = float(dur_out.strip())
                trim_dur = duration - 0.33
                f.write(f"file '{clip_path}'\n")
                f.write(f"duration {trim_dur}\n")
                
                # Add transition
                f.write(f"file '{transition_videos[i]}'\n")
            else:
                f.write(f"file '{clip_path}'\n")
    
    print(f"Concatenating final video...")
    run(f"ffmpeg -y -f concat -safe 0 -i '{concat_file}' -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p '{OUTPUT}'")
    
    final_size = OUTPUT.stat().st_size / (1024*1024)
    print(f"\n{'=' * 60}")
    print(f"✓ Done: {OUTPUT} ({final_size:.1f}MB)")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
