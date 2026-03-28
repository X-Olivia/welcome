#!/usr/bin/env python3
"""Simple camera viewer for SO-101 robot arm camera."""

import argparse
import cv2


def main():
    parser = argparse.ArgumentParser(description="View camera feed")
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="Camera device index (default: 0)",
    )
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.device)
    if not cap.isOpened():
        print(f"Error: Could not open camera at /dev/video{args.device}")
        return 1

    print(f"Camera opened successfully. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame")
            break

        cv2.imshow("SO-101 Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    exit(main())
