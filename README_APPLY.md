# Applying the voice-streaming changes

`CHANGES.diff` contains only the progressive voice-stream implementation and its directly related tests. Pre-existing workspace changes were intentionally excluded and left untouched.

Apply the patch on a clean checkout of the same repository revision:

```powershell
git apply --check CHANGES.diff
git apply CHANGES.diff
```

The patch is already represented in this working tree, so do not apply it here. It was checked against the repository index with `git apply --check --cached CHANGES.diff`.

The change adds an opt-in voice-chat route, authenticated per-user sentence polling, bounded Ollama streaming for eligible grounded/tool-free responses, sentence-level validation, and sequential browser TTS playback. Other providers and tool/regeneration paths keep their existing full-response flow. Existing speech profile configuration is retained; speech endpoints remain local-only and disabled outside debug mode.

No commit or push was made.

## Manual local verification

With the project running in local debug mode and the existing local speech services configured, verify:

1. Recording starts and stops from the microphone button, then transcribes and submits automatically.
2. Arabic output uses the configured Egyptian voice reference and begins speaking before the complete answer arrives.
3. English, French, and German output continues to use the configured general voice profile.
4. The speaker/stop controls stop current audio immediately, and text-only chat remains unchanged.
5. In a cloud/non-debug deployment, STT and TTS remain unavailable.

See `TEST_REPORT.md` for automated validation and what still requires local-device testing.
