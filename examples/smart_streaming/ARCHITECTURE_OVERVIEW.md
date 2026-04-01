# PicoScope Streaming Application - Architecture Overview

## 📋 Table of Contents
1. [Project Structure](#project-structure)
2. [File Descriptions](#file-descriptions)
3. [Module Interactions](#module-interactions)
4. [Data Flow](#data-flow)
5. [Threading Architecture](#threading-architecture)
6. [Performance Considerations](#performance-considerations)

---

## 🏗️ Project Structure

```
Smart_Streaming/
├── direct_streaming_plot_downsampled.py    # Main application (2,323 lines)
├── hardware_helpers.py                     # Hardware management (631 lines)
├── data_processing.py                       # Data processing & plotting (546 lines)
├── ui_helpers.py                           # UI management & coordination (904 lines)
├── ui_components.py                        # UI widget creation (2,457 lines)
└── ARCHITECTURE_OVERVIEW.md                # This documentation
```

**Total Codebase:** ~6,861 lines (modular architecture with comprehensive functionality)

---

## 📁 File Descriptions

### 🎯 `direct_streaming_plot_downsampled.py` - Main Application
**Purpose:** Central orchestrator and application entry point
**Size:** 2,323 lines

**Key Responsibilities:**
- **Application Initialization:** Sets up PyQtGraph, hardware connection, and UI
- **Configuration Management:** Defines global constants and settings
- **Thread Coordination:** Manages streaming thread and UI thread communication
- **Event Loop:** Handles Qt application lifecycle and cleanup
- **Signal Handling:** Connects UI events to appropriate handlers

**Core Components:**
```python
# Configuration Constants
SAMPLES_PER_BUFFER = 1000000
TARGET_TIME_WINDOW = 1.0
DOWNSAMPLING_RATIO = 640
REFRESH_FPS = 30

# Global State Variables
hardware_adc_sample_rate = 0
streaming_stopped = False
data_lock = threading.Lock()

# Main Functions
def on_apply_button_clicked()    # Settings update orchestrator
def on_stop_button_clicked()     # Stop/restart handler
def streaming_thread()           # Data acquisition thread
def cleanup()                    # Resource cleanup
```

---

### 🔧 `hardware_helpers.py` - Hardware Management
**Purpose:** All PicoScope hardware operations and calculations
**Size:** 631 lines

**Key Responsibilities:**
- **Hardware Control:** Start/stop streaming, buffer management
- **Sample Rate Calculations:** Convert intervals to rates, MSPS calculations
- **Buffer Optimization:** Calculate optimal buffer sizes based on memory
- **Trigger Management:** Configure and apply trigger settings
- **Memory Validation:** Ensure buffer sizes don't exceed device limits

**Core Functions:**
```python
# Hardware Control
def stop_hardware_streaming(scope)
def clear_hardware_buffers(scope)
def register_double_buffers(scope, buffer_0, buffer_1, ...)
# Note: Use scope.run_streaming() directly to start streaming

# Calculations
def calculate_sample_rate(interval, time_unit)
def calculate_optimal_buffer_size(max_memory, ratio)
def time_to_samples(time_value, time_unit, sample_rate_hz)

# Mode-Specific Datatype Handling
def get_datatype_for_mode(downsampling_mode)
    # Returns correct datatype: AVERAGE→INT16_T, DECIMATE→INT8_T

# Trigger Management
def configure_default_trigger(scope, enabled, threshold)
def apply_trigger_configuration(scope, enabled, threshold)

# Raw Data Operations
def pull_raw_samples_from_device(scope, total_raw_samples, adc_data_type)
def get_trigger_position_from_device(scope, trigger_at_sample, downsampling_ratio)

# Validation
def validate_buffer_size(buffer_size, ratio, max_memory)
```

**Dependencies:**
- `pypicosdk` - PicoScope SDK
- `numpy` - Numerical calculations

---

### 📊 `data_processing.py` - Data Processing & Plotting
**Purpose:** Real-time data processing, plotting, and performance monitoring
**Size:** 546 lines

**Key Responsibilities:**
- **Plot Updates:** Efficient real-time plot rendering
- **Data Visualization:** Scatter plot creation and optimization
- **Performance Monitoring:** Efficiency tracking and status display
- **Buffer Management:** Ring buffer operations and status updates
- **UI Status Updates:** Real-time performance indicators

**Core Functions:**
```python
# Plot Management
def update_plot(curve, data_array, ring_head, ring_filled, ...)
def create_plot_curve(plot, antialias)
def create_raw_data_curve(plot, antialias, downsample_mode)
def setup_plot_optimizations(plot, time_window, sample_rate, scope, datatype)

# ADC Limits & Y-Axis Management
def update_y_axis_from_adc_limits(plot, scope, datatype)
def enforce_y_axis_adc_limits(plot, scope, buffer_percent, datatype)

# Status Updates
def calculate_efficiency_status(efficiency_history)
def update_performance_tracking(perf_window, window_secs, n_samples)

# Buffer Operations
def drain_remaining_buffers(scope, buffer_0, buffer_1, ...)
def calculate_raw_data_time_alignment(ring_filled, downsampling_ratio, ...)

# Utilities
def format_memory_size(bytes_value)
```

**Dependencies:**
- `pyqtgraph` - Plotting library
- `numpy` - Data processing
- `pypicosdk` - Hardware data access

---

### 🎨 `ui_helpers.py` - UI Management & Coordination
**Purpose:** UI event handling, settings management, and user interaction coordination
**Size:** 904 lines

**Key Responsibilities:**
- **Settings Collection:** Gather values from UI widgets
- **Change Detection:** Determine what settings have changed
- **Settings Validation:** Validate and optimize user inputs
- **Settings Application:** Apply changes to hardware and UI
- **Streaming Control:** Coordinate streaming restarts and updates

**Core Functions:**
```python
# Settings Management
def collect_ui_settings(ratio_spinbox, mode_combo, ...)
def calculate_what_changed(settings, current_settings)
def validate_and_optimize_settings(settings, max_memory, ...)

# Settings Application
def apply_performance_settings(settings, timer)
def apply_time_window(settings, settings_changed, ...)
def apply_streaming_restart(settings, scope, buffer_0, ...)
    # Handles mode changes, datatype changes, ADC limits updates
def apply_channel_siggen_settings(settings, scope)

# Streaming Control
def update_max_post_trigger_range(buffer_size, spinbox)
```

**Dependencies:**
- `hardware_helpers` - Hardware operations
- `time` - Timing operations
- `numpy` - Data processing

---

### 🖼️ `ui_components.py` - UI Widget Creation
**Purpose:** PyQt widget creation, styling, and layout management
**Size:** 2,457 lines

**Key Responsibilities:**
- **Widget Creation:** Build all UI components (spinboxes, buttons, etc.)
- **Styling:** Apply consistent dark theme styling
- **Layout Management:** Organize widgets into logical groups
- **Status Displays:** Create real-time status indicators
- **Control Panels:** Build complete control panel layouts

**Core Functions:**
```python
# Widget Creation
def create_spinbox_with_style(min_val, max_val, current_val, ...)
def create_double_spinbox_with_style(min_val, max_val, ...)
def create_status_display_widget(label_text, display_text, ...)

# Layout Management
def create_group_widget(title)
def create_label_with_style(text, style)
def create_separator()

# Control Panels
def create_downsampling_controls(psdk, current_ratio, current_mode)
def create_performance_controls(current_refresh_fps, current_poll_interval)
def create_trigger_controls(current_max_post_trigger_samples, ...)
def build_control_panel(config)
```

**Dependencies:**
- `pyqtgraph` - Qt widgets and styling

---

## 🔄 Module Interactions

### **Import Hierarchy:**
```
direct_streaming_plot_downsampled.py
├── hardware_helpers.py
├── data_processing.py
├── ui_helpers.py
│   └── hardware_helpers.py (imported)
└── ui_components.py
```

### **Interaction Patterns:**

#### 1. **Main → Hardware Helpers / SDK**
```python
# Hardware initialization and control
actual_interval = scope.run_streaming(sample_interval, time_units, ...)  # Direct SDK call
stop_hardware_streaming(scope)
register_double_buffers(scope, buffer_0, buffer_1, ...)
```

#### 2. **Main → Data Processing**
```python
# Plot management and updates
curve = data_processing.create_plot_curve(plot, ANTIALIAS)
data_processing.setup_plot_optimizations(plot, TARGET_TIME_WINDOW, ...)
plot_updated = data_processing.update_plot(curve, data_array, ...)
```

#### 3. **Main → UI Helpers**
```python
# Settings management and application
settings = collect_ui_settings(ratio_spinbox, mode_combo, ...)
settings_changed, performance_changed, ... = calculate_what_changed(settings, ...)
success = apply_streaming_restart(settings, scope, buffer_0, ...)
```

#### 4. **UI Helpers → Hardware Helpers**
```python
# Hardware operations from UI events
apply_trigger_configuration(scope, trigger_enabled, threshold)
optimal_buffer = calculate_optimal_buffer_size(max_memory, ratio)
is_valid, memory_required, percentage = validate_buffer_size(buffer_size, ...)
```

#### 5. **Main → UI Components**
```python
# UI creation and management
control_widgets = build_control_panel(config)
status_bar, status_displays = create_status_bar()
```

---

## 📈 Data Flow

### **Real-Time Data Flow:**
```
PicoScope Hardware
    ↓ (hardware streaming)
Hardware Buffers (buffer_0, buffer_1)
    ↓ (polling thread)
Streaming Thread (streaming_thread)
    ↓ (data processing)
Ring Buffer (data_array)
    ↓ (plot updates)
PyQtGraph Plot (curve)
    ↓ (UI updates)
Status Displays (status_displays)
```

### **Settings Update Flow:**
```
User Input (UI Widgets)
    ↓ (collect_ui_settings)
Settings Dictionary
    ↓ (calculate_what_changed)
Change Detection
    ↓ (validate_and_optimize_settings)
Validated Settings
    ↓ (apply_streaming_restart)
Hardware Reconfiguration
    ↓ (register_double_buffers)
New Hardware State
```

### **Performance Monitoring Flow:**
```
Hardware Data Acquisition
    ↓ (update_performance_tracking)
Performance Metrics
    ↓ (calculate_efficiency_status)
Efficiency Status
    ↓ (update_efficiency_display)
UI Status Indicators
```

---

## 🧵 Threading Architecture

### **Thread Structure:**
```
Main Thread (Qt Event Loop)
├── UI Thread (Qt GUI)
├── Streaming Thread (Data Acquisition)
└── Timer Thread (Plot Updates)
```

### **Thread Communication:**
- **Qt Signals/Slots:** Thread-safe communication between threads
- **Threading Locks:** `data_lock` for shared data protection
- **Event Objects:** `settings_update_event` for coordination
- **Global Flags:** `stop_streaming`, `streaming_stopped` for control

### **Thread Responsibilities:**

#### **Main Thread:**
- Qt application event loop
- UI event handling
- Settings coordination
- Resource cleanup

#### **Streaming Thread:**
- Continuous hardware polling
- Data acquisition and processing
- Ring buffer management
- Performance tracking

#### **Timer Thread:**
- Regular plot updates (30 FPS)
- UI status updates
- Performance monitoring

---

## ⚡ Performance Considerations

### **Optimization Strategies:**

#### **1. Efficient Data Structures:**
- **Ring Buffer:** O(1) insertion, prevents memory fragmentation
- **NumPy Arrays:** Vectorized operations, C-level performance
- **Deque Collections:** Efficient FIFO for performance tracking

#### **2. Plotting Optimizations:**
- **Scatter Plot:** Individual points, no line rendering
- **Clip to View:** Only render visible data
- **Auto Downsample:** Disabled for manual control
- **Antialiasing:** Disabled for performance

#### **3. Threading Optimizations:**
- **Minimal Lock Time:** Short critical sections
- **Event-Driven Updates:** Only update when data changes
- **Background Processing:** Non-blocking hardware operations

#### **4. Memory Management:**
- **Pre-allocated Buffers:** Fixed-size arrays
- **Buffer Reuse:** Double buffering prevents allocation overhead
- **Mode-Specific Data Types:** 
  - DECIMATE mode: INT8_T for hardware (faster, less memory)
  - AVERAGE mode: INT16_T for hardware (required by hardware limitation)
  - Processing: FLOAT32 for all modes (consistent internal representation)

### **Performance Metrics:**
- **Plot Update Rate:** 30 FPS (configurable)
- **Hardware Polling:** 1ms intervals (configurable)
- **Memory Usage:** ~50MB for typical configuration
- **CPU Usage:** <10% on modern systems

---

## 🔧 Configuration Management

### **Global Configuration:**
```python
# Hardware Settings
SAMPLES_PER_BUFFER = 1000000
DOWNSAMPLING_RATIO = 640
DOWNSAMPLING_MODE = psdk.RATIO_MODE.DECIMATE

# Performance Settings
REFRESH_FPS = 30
POLLING_INTERVAL = 0.001

# Display Settings
TARGET_TIME_WINDOW = 1.0
ANTIALIAS = False
```

### **Dynamic Configuration:**
- **User-Adjustable:** All settings can be changed via UI
- **Real-Time Updates:** Performance settings apply immediately
- **Hardware Restart:** Streaming settings require hardware restart
- **Validation:** Automatic validation and optimization
- **Mode-Specific Handling:** Automatic datatype and ADC limits adjustment when switching between DECIMATE and AVERAGE modes

### **Average Downsample Mode Support:**
- **Mode Detection:** `get_datatype_for_mode()` returns correct datatype based on mode
- **Automatic Buffer Reallocation:** Hardware buffers reallocated with correct datatype when mode changes
- **ADC Limits Management:** Y-axis automatically updated when datatype changes (INT8_T ↔ INT16_T)
- **Hardware Limitation:** AVERAGE mode requires INT16_T (hardware constraint), DECIMATE can use INT8_T

---

## 🚀 Benefits of Modular Architecture

### **1. Maintainability:**
- **Single Responsibility:** Each module has a clear purpose
- **Easier Debugging:** Issues isolated to specific modules
- **Code Reuse:** Functions can be used across projects

### **2. Performance:**
- **Zero Runtime Impact:** Module separation doesn't affect execution
- **Faster Development:** Easier to optimize specific functions
- **Better Testing:** Individual modules can be unit tested

### **3. Scalability:**
- **Easy Extension:** New features can be added to appropriate modules
- **Plugin Architecture:** Helper modules can be swapped or extended
- **Team Development:** Multiple developers can work on different modules

### **4. Documentation:**
- **Clear Interfaces:** Well-defined function signatures
- **Modular Documentation:** Each module can be documented independently
- **Architecture Overview:** Clear understanding of system structure

---

## 📝 Development Guidelines

### **Adding New Features:**
1. **Identify Module:** Determine which module the feature belongs to
2. **Define Interface:** Create clear function signatures
3. **Update Documentation:** Document new functions and interactions
4. **Test Integration:** Ensure proper module interaction

### **Modifying Existing Features:**
1. **Locate Function:** Find the function in the appropriate module
2. **Understand Dependencies:** Check what other modules depend on it
3. **Update Tests:** Ensure changes don't break existing functionality
4. **Update Documentation:** Reflect changes in this overview

### **Performance Optimization:**
1. **Profile First:** Identify actual bottlenecks
2. **Module-Specific:** Focus optimization within appropriate modules
3. **Measure Impact:** Verify performance improvements
4. **Document Changes:** Update performance considerations

---

## 📚 Key Features & Implementations

### **Average Downsample Mode Support**

The application fully supports both DECIMATE and AVERAGE downsampling modes with automatic handling of mode-specific requirements:

**Key Implementation Details:**
- **Mode-Specific Datatypes:** AVERAGE mode requires INT16_T (hardware limitation), DECIMATE mode uses INT8_T
- **Automatic Buffer Management:** Buffers are automatically reallocated with correct datatype when mode changes
- **ADC Limits Management:** Y-axis automatically updates when switching modes to reflect correct ADC limits
- **Helper Function:** `get_datatype_for_mode()` in `hardware_helpers.py` centralizes datatype selection logic

**Implementation Locations:**
- `hardware_helpers.py`: `get_datatype_for_mode()` function
- `ui_helpers.py`: `apply_streaming_restart()` - handles mode changes and ADC limits updates
- `data_processing.py`: `update_y_axis_from_adc_limits()` - updates plot Y-axis for current datatype
- `direct_streaming_plot_downsampled.py`: Initial buffer creation and streaming thread use mode-specific datatypes

**Status:** ✅ Fully implemented and tested - ready for production use

---

*This architecture overview provides a comprehensive understanding of the PicoScope streaming application's modular design, enabling effective development, maintenance, and extension of the system.*
