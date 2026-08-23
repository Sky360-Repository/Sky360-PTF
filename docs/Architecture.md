# s360-ptf-node Architecture
Sky360 Project - PTF Node Specification

## 1. Overview

`s360-ptf-node` is the **precision tracking node** in the Sky360 system.
Its purpose is to:

- Receive **target positions** from s360-core-node or s360-asc-node
- Control a **Pan–Tilt–Focus (PTF)** camera system
- Acquire frames from the **PTF camera** (same controller as ASC)
- Run **target tracking** (EKF-based, deterministic)
- Run **TinyML inference** on the NPU for semantic classification
- Publish structured protobuf messages over **eCAL**
- Provide real-time tracking feedback to ASC, CORE, and NAS nodes

## 2. High-Level Architecture

```
s360-ptf-node
 +-- orchestrator/
 |     +-- main orchestrator loop
 |     +-- module lifecycle mgmt
 |     +-- eCAL publishers/subscribers
 |     +-- target routing + control feedback
 |
 +-- ptf-control/
 |     +-- pan/tilt motor controller
 |     +-- focus controller
 |     +-- target position interpreter
 |     +-- pb.sky.PtfStatus publisher
 |
 +-- camera/
 |     +-- PTF camera controller (QHY/ZWO/USB)
 |     +-- RAW frame acquisition
 |     +-- pb.sky.AllSkyCameraData publisher
 |
 +-- tracking/
 |     +-- EKF-based target tracking
 |     +-- motion model + measurement model
 |     +-- pb.sky.PtfTrack publisher
 |
 +-- tinyml/
       +-- NPU inference (classification)
       +-- semantic labeling of tracked objects
       +-- pb.sky.PtfSemanticEvent publisher
```

## 3. Component Responsibilities

### **Orchestrator**
- Starts/stops modules
- Routes target positions - PTF control
- Routes camera frames - tracking - TinyML
- Publishes heartbeat/status
- Manages eCAL publishers/subscribers
- Ensures deterministic control loop timing
- Handles backpressure (frame dropping, queue limits)

### **PTF Control Module**
- Receives target positions (azimuth, elevation, focus)
- Converts target coordinates into motor commands
- Controls pan, tilt, and focus motors
- Publishes `PtfStatus` (angles, focus, motor state)
- Provides closed-loop control feedback

### **PTF Camera Module**
- Interfaces with QHY, ZWO, USB cameras
- Acquires RAW frames (RAW8/RAW12/RAW16)
- Publishes `pb.sky.AllSkyCameraData`
- Provides sensor metadata (gain, exposure, temperature)

### **Tracking Module**
- Runs EKF-based tracking
- Fuses motor angles + camera detections
- Predicts future target positions
- Publishes `PtfTrack`
- Provides stable tracking even with noisy detections

### **TinyML Module**
- Runs NPU inference on tracked ROIs
- Classifies objects (aircraft, drone, bird, unknown)
- Publishes `PtfSemanticEvent`
- Provides confidence scores

# 4. Interfaces

Below are the formal interface definitions for **data flow**, **processing stages**, **inputs**, **outputs**, and **eCAL topics**.

## 4.1 DATA FLOW & ARCHITECTURE

| Component | Direction | Data Type | Topic | Description |
|----------|-----------|-----------|--------|-------------|
| PTF Control | In | `TargetMessage` | `sky360/ptf/target` | Target az/el/focus from CORE/ASC |
| PTF Control | Out | `PtfStatus` | `sky360/ptf/status` | Motor angles + focus state |
| PTF Camera | Out | `pb.sky.AllSkyCameraData` | `sky360/ptf/frame` | RAW frame + metadata |
| Tracking Module | Out | `PtfTrack` | `sky360/ptf/track` | EKF target state |
| TinyML Module | Out | `PtfSemanticEvent` | `sky360/ptf/semantic` | Classified tracked object |
| Orchestrator | Out | `PtfNodeStatus` | `sky360/ptf/node_status` | Node health |
| Orchestrator | In | `TimingMessage` | `sky360/timing` | GNSS time alignment |

## 4.2 PROCESSING STAGES

| Stage | Process | Input | Output | Configurable | Notes |
|-------|---------|--------|---------|--------------|-------|
| Target Acquisition | Receive target | TargetMessage | Target vector | None | From CORE or ASC |
| PTF Control | Motor control | Target vector | PtfStatus | PID gains | Pan/tilt/focus |
| Frame Acquisition | RAW capture | Camera | RAW frame | Gain, exposure | Same as ASC |
| Tracking | EKF | Frame + PTF angles | PtfTrack | Motion model | Predictive tracking |
| TinyML | NPU inference | ROI | Semantic event | Model path | RK3588 NPU |

## 4.3 INPUT FIELDS (PTF - node)

### **TargetMessage Input Fields**

| Field Name | Proto Type | Required | Default | Range/Values | Description |
|------------|------------|----------|---------|--------------|-------------|
| pan_deg | float | Yes | - | 0..360 | Target azimuth |
| tilt_deg | float | Yes | - | -90..90 | Target elevation |
| focus | float | Optional | 0.0 | 0..1 | Normalized focus |
| timestamp | Timestamp | Yes | - | GNSS time | Target timestamp |

## 4.4 OUTPUT FIELDS (PTF - other nodes)

### **PTF Status Output**

| Field | Type | Description |
|-------|------|-------------|
| pan_deg | float | Current pan angle |
| tilt_deg | float | Current tilt angle |
| focus | float | Current focus |
| motor_state | string | idle/moving/error |
| timestamp | Timestamp | Status time |

### **PTF Track Output (EKF)**

| Field | Type | Description |
|-------|------|-------------|
| track_id | string | Unique ID |
| pan_deg | float | Estimated azimuth |
| tilt_deg | float | Estimated elevation |
| velocity | float | Angular velocity |
| confidence | float | 0.0–1.0 |
| timestamp | Timestamp | Track time |

### **PTF Semantic Event Output (TinyML)**

| Field | Type | Description |
|-------|------|-------------|
| track_id | string | ID from EKF |
| label | string | aircraft/drone/bird/unknown |
| confidence | float | 0.0-1.0 |
| timestamp | Timestamp | Classification time |

# 5. eCAL TOPIC DEFINITIONS

| Topic Name | Direction | Message Type | Description |
|------------|-----------|--------------|-------------|
| `sky360/ptf/target` | In | `TargetMessage` | Target position from CORE/ASC |
| `sky360/ptf/status` | Out | `PtfStatus` | Motor angles + focus |
| `sky360/ptf/frame` | Out | `pb.sky.AllSkyCameraData` | RAW frame + metadata |
| `sky360/ptf/track` | Out | `PtfTrack` | EKF target state |
| `sky360/ptf/semantic` | Out | `PtfSemanticEvent` | TinyML classification |
| `sky360/ptf/node_status` | Out | `PtfNodeStatus` | Node health |
| `sky360/timing` | In | `TimingMessage` | GNSS time alignment |
