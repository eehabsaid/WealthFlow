# Voice-streaming test report

## Automated checks

- Django focused suite: `python manage.py test core.tests.ai.test_voice_stream core.tests.ai.test_speech_views core.tests.ai.test_speech_api core.tests.ai.test_chat_pipeline` — **54 tests passed**.
- JavaScript lint: `npm run lint:js` — **passed**.
- Django configuration: `python manage.py check` — **passed**.
- Whitespace validation: `git diff --check` — **passed**.
- Delivery patch validation: `git apply --check --cached CHANGES.diff` — **passed**.
- New and modified code files remain below the 200-line limit.

## Browser checks

A temporary headless Chromium harness mocked the sentence-poll and synthesis endpoints:

- Two streamed sentences were synthesized and played in order; playback ended with no active audio and the speaking state reset.
- A sentence began playing while the mocked response was still incomplete. Calling the stop control immediately paused the active audio and cleared the active-audio count.
- The harness exposed and verified a queue-drain completion bug; the playback loop now exits when the stream is done and no audio remains.
- The temporary harness and loopback server were removed/stopped.

## Not exercised end-to-end

Live Whisper/Chatterbox model inference and physical microphone/speaker behavior were not exercised by the mocked browser harness. Follow the local manual checks in `README_APPLY.md`, especially Egyptian Arabic reference-voice pronunciation and the configured English/French/German profiles.

The progressive path intentionally applies to eligible Ollama grounded/tool-free generations. Other providers, tool calls, and regeneration continue through the existing complete-response path.
