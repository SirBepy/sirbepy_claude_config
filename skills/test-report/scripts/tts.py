"""Local narration voice. Reads one JSON request per stdin line, {"text": ..., "out": ...}, writes a
mono 16-bit 24kHz WAV, and answers one JSON line. One long-lived process, because loading the model
takes seconds and a take speaks dozens of lines."""
import json
import os
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

VOICE = "af_heart"


def main() -> None:
    models = sys.argv[1]
    kokoro = Kokoro(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))
    print(json.dumps({"ready": True}), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        try:
            samples, rate = kokoro.create(request["text"], voice=VOICE, speed=1.0, lang="en-us")
            # Written beside the target, then renamed, so a killed run never leaves a truncated clip in the cache.
            temp = request["out"] + ".tmp"
            sf.write(temp, samples, rate, subtype="PCM_16", format="WAV")
            os.replace(temp, request["out"])
            print(json.dumps({"ok": True, "rate": rate}), flush=True)
        except Exception as error:  # Reported to the recorder, which fails the take loudly.
            print(json.dumps({"ok": False, "error": str(error)}), flush=True)


if __name__ == "__main__":
    main()
