# Changelog

## January 2026 - Latest Updates

### Updated for Latest OpenAI Realtime API

- **Model**: Updated from `gpt-4o-realtime-preview-2024-12-17` to `gpt-realtime` (latest stable)
- **SDK**: Updated to OpenAI Python SDK 1.102.0+
- **Voice**: Changed default voice to `marin` (latest option), with support for `cedar` and classic voices
- **API Endpoint**: Using latest WebSocket endpoint format

### Key Changes

1. **Model Name**: `gpt-realtime` instead of preview versions
2. **Voice Options**: Added support for new voices (`marin`, `cedar`)
3. **SDK Version**: Minimum version requirement updated to 1.102.0
4. **Documentation**: Updated README with latest API information

### Compatibility

- Python 3.8+
- OpenAI Python SDK 1.102.0+
- Requires Realtime API access (may be in beta/preview)

### Migration Notes

If you were using an older version:
- Update your model parameter from preview versions to `gpt-realtime`
- Update OpenAI SDK: `pip install --upgrade openai`
- Check that your API key has access to the latest Realtime API
