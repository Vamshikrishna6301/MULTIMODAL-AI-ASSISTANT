# Multimodal Accessibility AI Assistant

Production-oriented Windows accessibility assistant designed for hands-free computer control using voice, accessibility APIs, UI automation, vision, and deterministic safety checks.

## Project Vision

The assistant is designed to support:

- visual impairments
- motor disabilities
- accessibility-first computing
- hands-free desktop use

Goal:

Allow a user to control a Windows computer without touching the keyboard or mouse while receiving spoken feedback similar to a screen reader.

Example interaction:

User:

`open chrome`

Assistant:

`Opening your browser.`

User:

`read screen`

Assistant:

`You are in Chrome. Button: Back. Button: Forward. Button: Reload.`

## High-Level Architecture

```text
Voice / Vision / Context
        ->
Intent Parser
        ->
Fusion Engine
        ->
Safety Engine
        ->
Decision Router
        ->
Execution Engine
        ->
Accessibility / Vision / OS Adapters
        ->
Speech Feedback
```

Primary runtime pipeline:

```text
Voice -> STT -> Intent Parser -> Fusion -> Safety -> Router -> Executor -> Accessibility Navigator / Vision Executor -> TTS
```

## System Architecture

The assistant uses a layered, mostly deterministic architecture.

```text
Voice Input
   ->
Speech Recognition (Faster-Whisper)
   ->
Intent Parsing
   ->
Context Memory
   ->
Fusion Engine
   ->
Safety Engine
   ->
Decision Router
   ->
Execution Engine
   ->
Accessibility Navigator / Vision Executor / Adapters
   ->
Speech Output
```

Each layer has a clear responsibility to preserve safety, predictability, and debuggability.

## Current Project Structure

```text
KRISHNA/
|
|-- core/
|   |-- context_memory.py
              |   |-- fusion_engine.py
|   |-- intent_parser.py
|   |-- intent_schema.py
|   |-- mode_manager.py
|   |-- neural_intent_classifier.py
|   |-- response_model.py
|   |-- safety_engine.py
|   |-- safety_rules.py
|   |-- task_planner.py
|
|-- data/
|
|-- execution/
|   |-- accessibility/
|   |   |-- accessibility_navigator.py
|   |   |-- navigation_orchestrator.py
|   |   |-- navigation_state.py
|   |   |-- accessibility_tree_builder.py
|   |   |-- accessibility_tree.py
|   |   |-- browser_detector.py
|   |   |-- browser_dom_reader.py
|   |   |-- dom_region_analyzer.py
|   |   |-- perception_engine.py
|   |   |-- perception_filter.py
|   |   |-- semantic_model.py
|   |   |-- semantic_navigator.py
|   |   |-- noise_filter.py
|   |   |-- output_filter.py
|   |   |-- ui_element.py
|   |   |-- uia_focus_event_listener.py
|   |   |-- focus_event_monitor.py
|   |   |-- keyboard_navigation.py
|   |   |-- screen_reader_flag.py
|   |   |-- nvda_bridge.py
|   |   |-- nvda_reader.py
|   |
|   |-- adapters/
|   |   |-- windows_app.py
|   |   |-- windows_browser.py
|   |   |-- windows_file.py
|   |   |-- windows_keyboard.py
|   |   |-- windows_system.py
|   |
|   |-- ui/
|   |   |-- semantic_ui_engine.py
|   |
|   |-- uia_service/
|   |   |-- ui_client.py
|   |   |-- ui_server.py
|   |
|   |-- vision/
|   |   |-- camera_detector.py
|   |   |-- click_engine.py
|   |   |-- element_selector.py
|   |   |-- event_engine.py
|   |   |-- grounding.py
|   |   |-- layout_analyzer.py
|   |   |-- ocr_engine.py
|   |   |-- scene_graph_engine.py
|   |   |-- scene_memory.py
|   |   |-- screen_capture.py
|   |   |-- screen_element_graph.py
|   |   |-- screen_element.py
|   |   |-- screen_monitoring_engine.py
|   |   |-- stabilization_buffer.py
|   |   |-- tracking_engine.py
|   |   |-- ui_detector.py
|   |   |-- vision_executor.py
|   |   |-- vision_mode_controller.py
|   |   |-- vision_query_engine.py
|   |
|   |-- app_control.py
|   |-- dispatcher.py
|   |-- execution_hardening.py
|   |-- execution_logger.py
|   |-- executor.py
|   |-- key_ops.py
|   |-- keyboard_mouse.py
|   |-- performance_layer.py
|   |-- plugin_system.py
|
|-- infrastructure/
|   |-- cache.py
|   |-- config_manager.py
|   |-- error_handling.py
|   |-- health_monitor.py
|   |-- logger.py
|   |-- persistence.py
|   |-- production_logger.py
|   |-- runtime_recovery.py
|   |-- system_monitor.py
|   |-- validation.py
|   |-- watchdog.py
|
|-- knowledge/
|   |-- knowledge_engine.py
|   |-- llm_engine.py
|
|-- plugins/
|   |-- system_status_plugin.py
|
|-- router/
|   |-- decision_router.py
|
|-- utility/
|   |-- utility_engine.py
|
|-- voice/
|   |-- assistant_runtime.py
|   |-- audio_guard.py
|   |-- mic_stream.py
|   |-- stt.py
|   |-- stt_fixed.py
|   |-- tts.py
|   |-- vad.py
|   |-- voice_loop.py
|   |-- wakeword.py
|
|-- tests/
|-- tools/
|-- models/
|-- logs/
|-- main.py
|-- config.py
|-- config_production.py
|-- validate_production.py
|-- README.md
|-- PRODUCTION_CHECKLIST.md
|-- requirements.txt
```

## Core Modules

### `core/`

- `intent_parser.py`
  - deterministic intent parsing
- `neural_intent_classifier.py`
  - sentence-transformer / FAISS fallback
- `fusion_engine.py`
  - merges parser, context, and neural fallback
- `safety_engine.py`
  - confirmation and risk rules
- `context_memory.py`
  - conversational memory and follow-up resolution
- `task_planner.py`
  - multi-step decomposition for compound commands

### `voice/`

- `voice_loop.py`
  - live voice ingestion and command execution flow
- `stt.py`
  - Whisper-based speech-to-text
- `tts.py`
  - spoken response output
- `vad.py`
  - speech activity detection
- `assistant_runtime.py`
  - speech/listening runtime guards
- `audio_guard.py`
  - echo and self-transcription suppression

### `execution/`

- `dispatcher.py`
  - action routing to adapters, vision, plugins
- `executor.py`
  - high-level execution orchestration
- `execution_hardening.py`
  - retries, rollback hooks, circuit breaker logic
- `performance_layer.py`
  - response caching and timing
- `plugin_system.py`
  - plugin discovery and dispatch

### `execution/accessibility/`

- `accessibility_navigator.py`
  - main accessibility facade
- `navigation_orchestrator.py`
  - unified focus / keyboard / scan strategy chooser
- `uia_focus_event_listener.py`
  - UIA focus event integration
- `keyboard_navigation.py`
  - Tab and Shift+Tab navigation support
- `nvda_reader.py`
  - NVDA-assisted read path with fallback
- `nvda_bridge.py`
  - older / alternate NVDA-related integration helper

### `execution/vision/`

- `vision_executor.py`
  - orchestrates screen and camera vision tasks
- `ocr_engine.py`
  - OCR extraction
- `ui_detector.py`
  - Ultralytics-based UI detection
- `camera_detector.py`
  - live camera scene detection
- `element_selector.py`
  - ranking for grounded visual interaction
- `grounding.py`
  - language-to-visual target grounding

### `infrastructure/`

- structured logging
- persistence
- health monitoring
- watchdogs
- runtime recovery
- validation

## Phases and Status

### Phase 1 - Intent and Safety Engine

Status: Implemented and active

Includes:

- deterministic intent parser
- neural intent fallback
- safety engine
- fusion engine
- context integration

Example supported intents:

- `open chrome`
- `search python tutorial`
- `delete file test.txt`
- `shutdown computer`

Safety examples:

- dangerous file deletion can be blocked
- shutdown requires confirmation
- risky actions carry confirmation metadata

### Phase 2 - Voice Runtime

Status: Implemented, improved, still needs extended field validation

Technologies:

- Faster-Whisper
- WebRTC VAD
- PyTorch CUDA
- pyttsx3
- sounddevice

Capabilities:

- real-time voice commands
- segmentation and silence detection
- interrupt handling
- basic echo suppression
- self-transcription suppression
- background command execution so long actions do not block the input loop

### Phase 3 - Execution Engine

Status: Implemented and hardened, still stabilizing across more real workflows

Includes:

- dispatcher-based execution
- Windows adapters
- retry logic
- rollback hooks
- execution tracing
- persistent execution logging

Adapters:

- `windows_app`
- `windows_browser`
- `windows_file`
- `windows_keyboard`
- `windows_system`

### Phase 4 - Accessibility Navigation

Status: Implemented, but still the most critical stabilization area

Capabilities currently present:

- `read screen`
- `read current`
- `next item`
- `previous item`
- `activate`
- semantic next navigation:
  - `next button`
  - `next link`
  - `next input`
  - `next tab`
  - `next menu`

Architecture:

1. Focus-based navigation
2. Keyboard navigation
3. UI tree scanning
4. NVDA-assisted reading with fallback

### Phase 5 - Vision

Status: Implemented in code, partially validated

Includes:

- OCR
- UI detection
- screen capture
- visual grounding
- click by textual or visual description
- camera scene detection

Examples:

- `click login button`
- `click red icon`
- `read text on screen`

### Phase 6 - Context and Multi-Step Planning

Status: Implemented

Includes:

- conversational memory
- follow-up resolution
- entity carry-forward
- multi-step task planning

Example:

`open chrome and search youtube`

### Phase 7 - Production Infrastructure

Status: Implemented in code, still needs wider runtime validation

Includes:

- persistent logging
- replay support
- watchdogs
- runtime recovery
- performance caching
- plugin system

## Vision System Details

The vision stack includes:

- screen capture
- OCR extraction
- Ultralytics GPU-backed detection when available
- UIA and OCR fusion
- element ranking
- click execution
- camera scene description

Current practical limitations:

- OCR quality depends on scaling, theme, and contrast
- object detection quality depends on model/device availability
- some apps expose better UIA than vision, so results vary by target application
- camera features exist in code but are not fully exposed through natural voice commands

## Accessibility Navigation Design

The navigator now combines several strategies:

### 1. Focus-Based Navigation

Uses UIA focus when available.

Pros:

- fast
- low latency
- good for keyboard-driven apps

Cons:

- stale or noisy in some applications

### 2. Keyboard Navigation

Uses `TAB`, `SHIFT+TAB`, and activation keys as fallback movement.

Pros:

- useful when focus tracking is weak

Cons:

- depends on the app respecting standard keyboard traversal

### 3. UI Tree Scanning

Scans a bounded portion of the accessibility tree.

Pros:

- allows screen summaries even without usable focus

Cons:

- slower
- quality depends on the application’s UIA tree

### 4. NVDA-Assisted Reading

Uses `nvdaControllerClient.dll` when available.

Pros:

- better alignment with screen-reader output patterns

Cons:

- depends on NVDA being installed and available
- does not yet provide full review-cursor parity

## Current Working Features

These features are implemented and reasonably usable for development and demos:

- voice command ingestion
- STT on CUDA-capable setups
- basic app opening
- keyboard typing actions
- browser/search-style actions
- safety confirmations
- context-aware follow-up memory
- multi-step task planning
- execution trace logging
- plugin loading
- UIA accessibility navigation primitives
- grounded visual click flow

## Current Problematic / Not Fully Working Features

This section is the most important operationally.

### `read screen`

Current state:

- implemented
- no longer freezes the voice loop the way it did before
- now returns a string instead of the old tuple contract
- now uses partial-result fallback instead of hard failing on timeout

Still problematic:

- still inconsistent across many apps
- often produces generic summaries instead of true screen-reader-quality output
- may depend on stale focus or shallow cached elements
- still not fully reliable in VS Code, browsers, File Explorer, and Electron apps

### Other Read Commands

Commands with partial or inconsistent behavior:

- `read current line`
- `read current`
- `what is this`
- `what is focused`
- `read focused element`

Reasons:

- these are mostly focus-summary based, not true review-cursor reading
- line-level reading is not fully implemented
- behavior varies heavily by application accessibility exposure

### `open camera`

Current state:

- camera functionality exists in `execution/vision/camera_detector.py`
- `VisionExecutor` supports camera handling internally

Still problematic:

- `open camera` is not cleanly wired as a natural parser intent
- the voice path for camera control is incomplete
- camera startup can fail if:
  - OpenCV cannot open the device
  - no camera is available
  - the YOLO model is unavailable
  - GPU/runtime dependencies are missing

### Navigation Commands

Commands still needing more validation:

- `next item`
- `previous item`
- `next button`
- `next link`
- `next input`
- `next tab`
- `next menu`
- `focus input`
- `activate`

Reasons:

- some apps emit noisy focus
- some apps do not support useful keyboard traversal
- some apps expose poor UIA trees

### Vision Features

Implemented, but not fully validated:

- `click login button`
- `click red icon`
- screen text reading
- screen monitoring

Remaining issues:

- OCR quality can degrade badly on some apps
- detections can miss low-contrast or tiny controls
- UIA / OCR / vision fusion still needs more ranking refinement

### Voice Runtime Remaining Risks

- long-running accessibility and vision actions still need soak testing
- real-world microphone noise handling is improved but not fully field-tested
- speech interruption behavior needs more real-user validation

## Problems Found So Far and Their Status

### Fixed or Improved

- `read_screen()` tuple return contract
- `read screen` voice-loop freeze from synchronous execution
- debug log leakage to console during normal use
- GPU detection and CUDA runtime setup in the repaired environment
- NVDA bridge / reader integration path
- neural intent classifier reactivation
- execution retry / rollback hardening
- task planner introduction
- performance and recovery scaffolding

### Still Open or Partially Open

- true screen-reader-grade `read screen`
- true line-reading behavior for `read current line`
- fully wired camera voice commands
- app-by-app navigation consistency
- full regression test execution in the repaired environment

## Current Development Focus

The highest priorities remaining are:

1. accessibility read quality
2. navigation reliability
3. camera command wiring
4. cross-application validation
5. setup and deployment simplification

## What Is Left To Build

These items still need implementation or significant refinement:

- true current-line reading instead of focused-element summaries
- richer NVDA integration beyond basic controller-client speech hooks
- parser and executor support for explicit camera commands like `open camera` and `stop camera`
- better app-specific heuristics for browsers, editors, and file managers
- broader automated tests for live accessibility and vision flows
- cleaner installation/bootstrap flow for:
  - NVDA
  - Tesseract
  - CUDA-enabled PyTorch
  - local sentence-transformer model
- more complete user-facing documentation for degraded-mode operation

## Commands With Known Issues

Treat these as unstable, incomplete, or requiring more validation:

- `read screen`
- `read current line`
- `read current`
- `what is this`
- `what is focused`
- `next item`
- `previous item`
- `next button`
- `next link`
- `next input`
- `next tab`
- `next menu`
- `focus input`
- `open camera`
- some screen-grounded click commands on complex applications

## Environment and Runtime Notes

This project is Windows-specific.

Important runtime dependencies outside Python:

- Windows UI Automation support
- Tesseract OCR installed on the system
- optional NVDA installation for NVDA-assisted reading
- optional NVIDIA GPU with CUDA for best STT and vision performance

Recommended run path:

```powershell
deactivate
.\.venv\Scripts\Activate.ps1
python main.py
```

## Requirements

Python dependencies are listed in `requirements.txt`.

The repo currently relies on:

- audio libraries
- Windows automation libraries
- OCR and vision libraries
- CUDA-capable PyTorch stack
- neural embedding stack
- browser automation dependencies
- HTTP/monitoring utilities

## Summary

This repository now contains most of the intended system architecture in code, including:

- voice runtime
- fusion and safety
- execution hardening
- task planning
- context memory
- accessibility orchestration
- NVDA-assisted reading
- vision grounding
- plugin infrastructure
- production monitoring and recovery

But several accessibility-critical user experiences are still not fully production-grade yet, especially:

- `read screen`
- line-level reading commands
- navigation consistency across apps
- `open camera` voice command wiring

Use this repository as an advanced, actively stabilized accessibility assistant codebase rather than a finished end-user product.
