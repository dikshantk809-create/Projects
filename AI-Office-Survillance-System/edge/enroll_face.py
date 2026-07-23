#!/usr/bin/env python3
"""Enroll people's faces with their names.

Look at the webcam, type a name, and the system saves that face so it can
recognise the person later (and show their name in the live window + Excel).
You can add as many people as you like; run it again any time to add more.

The faces are saved to the file named by AICAM_FACE_DB (default: faces.pkl).
"""
from __future__ import annotations
import os
import time

import cv2

from aicam_platform.common import get_settings, get_logger
from aicam_platform.vision import FaceEngine

log = get_logger("enroll")
S = get_settings()
SAMPLES = 6          # how many good face shots to capture per person
TIMEOUT_S = 25       # give up capturing after this long


def capture(faces: FaceEngine, source, name: str) -> int:
    cap = cv2.VideoCapture(int(source) if str(source).isdigit() else source)
    if not cap.isOpened():
        print("  Camera nahi khula. AICAM_SOURCE check karo (0 ya 1).")
        return 0
    print(f"  '{name}' ka face capture ho raha hai - camera ke saamne dekho...")
    got = 0
    deadline = time.time() + TIMEOUT_S
    while got < SAMPLES and time.time() < deadline:
        ok, frame = cap.read()
        if not ok:
            continue
        added = False
        try:
            added = faces.enroll(name, frame)   # detects largest face, stores embedding
        except Exception as e:
            print(f"  (face model load/issue: {e})")
            break
        if added:
            got += 1
            print(f"  captured {got}/{SAMPLES}")
            time.sleep(0.4)
        try:
            msg = f"{name}: {got}/{SAMPLES}  (look at camera)"
            cv2.putText(frame, msg, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 0), 2, cv2.LINE_AA)
            cv2.imshow("Enroll face - press q to skip", frame)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
        except Exception:
            pass
    cap.release()
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    return got


def main():
    db = S.face_db
    faces = FaceEngine(ctx_id=-1)
    already = faces.load(db)
    print("=" * 56)
    print(" Face enrollment")
    print(f" Database: {os.path.abspath(db)}  (already has {already} people)")
    print(" Note: the first time, a face model (~300 MB) downloads once.")
    print("=" * 56)

    while True:
        name = input("\nName likho (jaise 'Dikshant'), ya khaali Enter = finish: ").strip()
        if not name:
            break
        got = capture(faces, S.source, name)
        if got:
            faces.save(db)
            print(f"  Saved '{name}' ({got} shots). Total enrolled: {len(faces.gallery)}")
        else:
            print("  Koi face capture nahi hua. Behtar roshni me dobara try karo.")
        more = input("  Aur kisi ko add karna hai? (y = haan / Enter = bas): ").strip().lower()
        if more not in ("y", "yes", "haan", "h"):
            break

    print(f"\nDone. {len(faces.gallery)} log enrolled: {', '.join(faces.gallery) or '(none)'}")
    print("Ab run_faces_demo.bat chalao - known faces par naam dikhega.")


if __name__ == "__main__":
    main()
