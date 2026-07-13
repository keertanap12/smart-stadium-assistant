# Stadium Ops Assistant 🏟️

**Stadium Ops Assistant** is a lightweight, real-time operations dashboard designed for modern stadium and tournament managers. Developed as a hackathon submission under the **Smart Stadiums & Tournament Operations** vertical, the app provides data-driven decision tools to streamline two critical components of event logistics: **Gate & Crowd Flow Control** and **Parking & Transport Allocation**.

---

## 🌟 Hackathon Vertical: Smart Stadiums & Tournament Operations

Managing stadium operations during peak tournament hours presents significant safety and logistical challenges. Inefficient crowd control at entry gates can lead to bottlenecks, safety hazards, and delays. Similarly, poorly managed parking allocations lead to traffic jams, VIP delay, and transport delays (e.g. team or shuttle buses).

**Stadium Ops Assistant** resolves these by offering:
1. **Dynamic Crowd Re-routing**: Analyzes entry gates to dynamically flag bottlenecks and recommend re-routing or gate closures.
2. **Intelligent Parking Dispatch**: Simulates vehicle arrival streams (cars/buses) and assigns them to optimal lots in real-time, enforcing custom space reservations for larger transport vehicles (buses).

---

## 🛠️ Technical Stack & Architecture

The app is built to be modular, fast, and beginner-friendly:
*   **Backend**: Python with **Flask** for API endpoint management and system logic.
*   **Frontend**: Plain semantic **HTML5**, modern styling with **Vanilla CSS3** (featuring a sports-dashboard dark theme with glassmorphism), and **JavaScript (ES6)** for asynchronous, interactive UI updates.
*   **Testing**: **pytest** for automated verification of business logic modules.
*   **Data Storage**: JSON-based mock databases to simulate real-time sensor streams without requiring heavy database installations.

---

## 🧠 Algorithmic Logic & Business Rules

### 1. Gate & Crowd Flow Module (`modules/gate_flow.py`)
This module reads active sensor metrics for each entrance gate and calculates `crowd_percentage` (`current_crowd_count` / `gate_capacity`):
*   **Critical Status (`crowd_percentage > 95%`)**: Recommends closing the gate temporarily and deploying staff to manage the bottleneck.
*   **Near Capacity Status (`crowd_percentage > 85%`)**: Recommends redirecting fans to the nearest gate currently operating under 60% capacity.
*   **Normal Status**: Indicates smooth operations; no action is required.
*   **Kickoff Countdown Rule**: If the time remaining to kickoff is **under 30 minutes** and **multiple gates** (2 or more) are flagged as "Near Capacity" or "Critical", the system triggers an emergency recommendation to **"Open overflow gate"** to relieve gate pressure.

### 2. Parking & Transport Allocator Module (`modules/parking_allocator.py`)
This module queues incoming vehicles in batches and allocates them using a **Best-Fit Capacity** algorithm:
*   **Allocation Rule**: Assigns each batch to the lot with the **most free capacity** (`lot_capacity - current_occupancy`) that can accommodate the entire batch count.
*   **Bus Space Reservation Buffer**: Buses are larger and require specialized handling. The algorithm enforces that buses can only be allocated to lots with **at least 5 free spaces reserved** for bus-sized parking.
*   **Overflow Dispatch Rule**: If, after simulating all current batch allocations, **all main lots** (excluding reserved overflow lots) are projected to exceed **90% occupancy**, the module advises the coordinator to **"Open overflow lot"**.

---

## 🚀 Running the App Locally

### Prerequisites
Make sure you have Python 3.8+ installed on your system.

### Step 1: Clone and Navigate
Navigate to the project directory:
```bash
cd C:\Users\mural\.gemini\antigravity\scratch\smart-stadium-assistant
```

### Step 2: Install Dependencies
Create a virtual environment (optional but recommended) and install the packages listed in `requirements.txt`:
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows Power Shell:
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### Step 3: Run the Application
Start the Flask local development server:
```bash
python app.py
```
By default, the application will run at **`http://127.0.0.1:5000/`**. Open this URL in your web browser to access the dashboard.

### Step 4: Run Unit Tests
To verify the core logic functions, run the test suite using `pytest`:
```bash
pytest
```

---

## ⚙️ Assumptions Made

1.  **Mock Sensor Feeds**: Since this is a hackathon prototype, we assume that physical IoT sensors (crowd cameras, parking gate transponders) send data to files in the `/data` folder (`mock_gates.json` and `mock_lots.json`). In a production setting, these JSON files would be updated by real-time IoT message queues (like MQTT or AWS IoT Core).
2.  **Sequential Arrival**: Vehicle batches are allocated in the order they are listed in `mock_batches.json` (sequentially from top to bottom) representing chronological expected arrival times.
3.  **Single-Lot Batch Allocations**: We assume that incoming batches are kept together and assigned to a single parking lot. If a batch contains more vehicles than any single lot's free capacity, it will remain `Unassigned` with an alert.
