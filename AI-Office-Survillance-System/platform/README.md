# aicam_platform — shared library

Reusable building blocks for all three camera systems. Install editable:

```bash
pip install -e "platform[detect,face,alerts]"
```

Modules: `common` (config, logging, events, geometry) · `vision` (detector, tracker,
face, zones) · `alerts` (multi-channel dispatcher) · `storage` (evidence recorder).
