#!/usr/bin/env python3
import os
import re
import subprocess
from natsort import natsorted
import pysrt

def get_video_duration(video_path):
    """Get video duration in milliseconds using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    duration_sec = float(result.stdout.decode().strip())
    return int(duration_sec * 1000)  # Convert to milliseconds

def extract_number(filename):
    """Extract number from filename, whether it's at the start or end"""
    # Try to match number at the start
    start_match = re.match(r'^(\d+)', filename)
    if start_match:
        return start_match.group(1)

    # Try to match number at the end (before extension)
    end_match = re.search(r'(\d+)(?:\.[^.]+)?$', filename)
    if end_match:
        return end_match.group(1)

    return None

def merge_srt_files(directory, output_file):
    # Find all srt and mov files with numeric prefixes or suffixes
    files = [f for f in os.listdir(directory) if extract_number(f)]
    paired_files = []

    for f in files:
        base = extract_number(f)
        if not base:
            continue

        ext = os.path.splitext(f)[1]
        if ext == '.srt':
            # Movie file has the same name, just different extension
            mov_file = os.path.splitext(f)[0] + '.mov'

            if mov_file in files:
                paired_files.append((
                    int(base),
                    os.path.join(directory, f),
                    os.path.join(directory, mov_file)
                ))

    # Sort files by numeric prefix
    paired_files = natsorted(paired_files, key=lambda x: x[0])

    merged_subs = pysrt.SubRipFile()
    cumulative_duration = 0

    print(paired_files)
    for idx, (num, srt_path, mov_path) in enumerate(paired_files):
        print(f"Processing {num}: {srt_path} and {mov_path}")
        # Get duration of previous video segments
        if idx > 0:
            cumulative_duration += get_video_duration(paired_files[idx-1][2])

        # Load current SRT file
        subs = pysrt.open(srt_path)

        # Shift timestamps for subsequent files
        if idx > 0:
            for sub in subs:
                sub.start += cumulative_duration
                sub.end += cumulative_duration

        # Add to merged list
        merged_subs += subs

    # Clean indexes and save
    merged_subs.clean_indexes()
    merged_subs.save(output_file, encoding='utf-8')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Merge sequential SRT files with video duration compensation')
    parser.add_argument('input_dir', help='Directory containing numbered SRT/MOV files')
    parser.add_argument('output_file', help='Path for merged SRT file')
    args = parser.parse_args()

    merge_srt_files(args.input_dir, args.output_file)
