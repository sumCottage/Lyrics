import os
import sys
import time
import threading
import pygame
import yt_dlp
import imageio_ffmpeg

"""Download the song locally as song.mp3 and then play it."""

# ------------ DOWNLOAD SONG (yt-dlp + ffmpeg) ------------
url = "https://www.youtube.com/watch?v=Gz38Yj09k3A"
target_mp3 = os.path.join(os.getcwd(), "song.mp3")

if os.path.exists(target_mp3):
    print("Audio already present:", target_mp3)
else:
    print("Downloading audio with yt-dlp...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(os.getcwd(), "song.%(ext)s"),
        "prefer_ffmpeg": True,
        "ffmpeg_location": ffmpeg_exe,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        # ensure stable sample rate for pygame
        "postprocessor_args": ["-ar", "44100"],
        "quiet": False,
        "noprogress": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # After postprocessing, song.mp3 should exist
    if not os.path.exists(target_mp3):
        # Fallback: find any song.* and rename if needed
        for fname in os.listdir(os.getcwd()):
            if fname.startswith("song.") and fname.endswith(".mp3"):
                target_mp3 = os.path.join(os.getcwd(), fname)
                break
    print("Downloaded:", target_mp3)

# ------------ SETUP PYGAME ------------
pygame.mixer.init(frequency=44100)
pygame.mixer.music.load(target_mp3)

# Start playing from 1:55 → 115 seconds
start_time = 115
pygame.mixer.music.play(start=start_time)

# ------------ CONTROLS (pause/resume/stop) ------------
pause_flag = threading.Event()
stop_flag = threading.Event()

def input_controls():
    global lyric_offset
    #print("Controls: p=pause, r=resume, s/q=stop, [ / ] nudge lyrics, o=offset")
    while not stop_flag.is_set():
        try:
            cmd = input().strip().lower()
        except EOFError:
            break
        if cmd == "p":
            if not pause_flag.is_set():
                pygame.mixer.music.pause()
                pause_flag.set()
                print("Paused")
        elif cmd == "r":
            if pause_flag.is_set():
                pygame.mixer.music.unpause()
                pause_flag.clear()
                print("Resumed")
        elif cmd == "[":
            lyric_offset -= 0.25
            print(f"Lyric offset: {lyric_offset:+.2f}s (earlier)")
        elif cmd == "]":
            lyric_offset += 0.25
            print(f"Lyric offset: {lyric_offset:+.2f}s (later)")
        elif cmd == "o":
            print(f"Lyric offset: {lyric_offset:+.2f}s")
        elif cmd in ("s", "q"):
            stop_flag.set()
            pygame.mixer.music.stop()
            print("Stopped")
            break

ctrl_thread = threading.Thread(target=input_controls, daemon=True)
ctrl_thread.start()

# ------------ LYRICS WITH TIMING (absolute seconds from playback start) ------------
# The first element of each tuple is an ABSOLUTE timestamp (in seconds)
# measured from when playback starts, not a relative delay.
lyrics = [
    (0, "Hoke tetho duur mein"),
    (2, "Khoya apne aap nu......"),
    (5, "Adda hissa mere dil da"),
    (7, "Hoeya tere khilaaf kyun..."),
    (10, "Adda dil chaunda ae tenu"),
    (12, "Karni chaunda baat kyun..."),
    (15, "Tareyaan di roshni de wangu"),
    (17, "Gal nal laaja raat nu"),
    (19, "Dil mere nu samjhaja"),
    (21, "Hathan wich hath tu paaja"),
    (24, "Pehlan jo dekhi nahi mein"),
    (27, "Aaisi duniya tu dikhaa ja")
]

lyric_offset = 0.0  # allow fine-tuning in real time

def show_lyrics():
    # Typewriter effect synced to the audio clock
    idx = 0
    total = len(lyrics)
    line_started = False
    typed_idx = 0
    char_delay = 0.01  # default; recomputed per line based on available window

    while idx < total and not stop_flag.is_set():
        if pause_flag.is_set():
            time.sleep(0.02)
            continue

        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            time.sleep(0.02)
            continue

        pos = pos_ms / 1000.0  # seconds since play() (doesn't advance while paused)
        cue_time, text = lyrics[idx]
        cue_time = float(cue_time)

        # Wait for cue
        if not line_started:
            if pos + lyric_offset >= cue_time:
                # Type so the last character lands exactly at the next cue.
                if idx + 1 < total:
                    char_delay = 0.12
                else:
                    # Last line: use a reasonable default
                    char_delay = 0.12

                line_started = True
                typed_idx = 0
                # Immediately render first character at cue
                # (the loop below will compute target based on elapsed)
            else:
                time.sleep(0.01)
                continue

        # How many characters should be visible by now?
        elapsed = (pos + lyric_offset) - cue_time
        target = int(elapsed / char_delay) + 1  # start typing at cue
        target = max(0, min(target, len(text)))

        # Print any missing characters
        while typed_idx < target and not stop_flag.is_set():
            sys.stdout.write(text[typed_idx])
            sys.stdout.flush()
            typed_idx += 1

        # If the line is complete, newline and advance
        if typed_idx >= len(text):
            sys.stdout.write("\n")
            sys.stdout.flush()
            idx += 1
            line_started = False
        else:
            time.sleep(0.01)

lyrics_thread = threading.Thread(target=show_lyrics, daemon=True)
lyrics_thread.start()

# Keep script running until song ends
try:
    while pygame.mixer.music.get_busy() and not stop_flag.is_set():
        time.sleep(0.2)
finally:
    stop_flag.set()