import pytest
from modules.gate_flow import process_gate_flow

def test_gate_flow_normal():
    gates = [
        {
            "gate_id": "Gate A",
            "current_crowd_count": 500,
            "gate_capacity": 1000,
            "time_to_kickoff_minutes": 45
        }
    ]
    results = process_gate_flow(gates)
    assert len(results) == 1
    assert results[0]["status"] == "Normal"
    assert results[0]["recommendation"] == "No action needed"
    assert results[0]["crowd_percentage"] == 0.5

def test_gate_flow_near_capacity():
    gates = [
        {
            "gate_id": "Gate B",
            "current_crowd_count": 880,
            "gate_capacity": 1000,
            "time_to_kickoff_minutes": 45
        }
    ]
    results = process_gate_flow(gates)
    assert len(results) == 1
    assert results[0]["status"] == "Near Capacity"
    assert "Redirect fans to nearest gate" in results[0]["recommendation"]

def test_gate_flow_critical():
    gates = [
        {
            "gate_id": "Gate C",
            "current_crowd_count": 960,
            "gate_capacity": 1000,
            "time_to_kickoff_minutes": 45
        }
    ]
    results = process_gate_flow(gates)
    assert len(results) == 1
    assert results[0]["status"] == "Critical"
    assert "Close gate temporarily, deploy staff" in results[0]["recommendation"]

def test_gate_flow_multiple_gates_kickoff_overflow():
    gates = [
        {
            "gate_id": "Gate A",
            "current_crowd_count": 960,
            "gate_capacity": 1000,
            "time_to_kickoff_minutes": 20
        },
        {
            "gate_id": "Gate B",
            "current_crowd_count": 880,
            "gate_capacity": 1000,
            "time_to_kickoff_minutes": 20
        },
        {
            "gate_id": "Gate C",
            "current_crowd_count": 300,
            "gate_capacity": 1000,
            "time_to_kickoff_minutes": 20
        }
    ]
    results = process_gate_flow(gates)
    # Gates A & B are critical/near capacity, and kickoff < 30 mins, so they should get "Open overflow gate" appended.
    # Gate C is normal, so its recommendation should not get "Open overflow gate" (only critical/near capacity gates get it, or wait...
    # let's check: "If time_to_kickoff_minutes < 30 and multiple gates are 'Near Capacity' or 'Critical' -> add recommendation = 'Open overflow gate'")
    # Our implementation appends it only if status in ["Critical", "Near Capacity"].
    assert "Open overflow gate" in results[0]["recommendation"]
    assert "Open overflow gate" in results[1]["recommendation"]
    assert "Open overflow gate" not in results[2]["recommendation"]

def test_gate_flow_validation_negative_crowd():
    gates = [
        {
            "gate_id": "Gate A",
            "current_crowd_count": -10,
            "gate_capacity": 1000,
            "time_to_kickoff_minutes": 40
        }
    ]
    with pytest.raises(ValueError, match="Crowd count cannot be negative"):
        process_gate_flow(gates)

def test_gate_flow_validation_zero_capacity():
    gates = [
        {
            "gate_id": "Gate A",
            "current_crowd_count": 10,
            "gate_capacity": 0,
            "time_to_kickoff_minutes": 40
        }
    ]
    with pytest.raises(ValueError, match="Capacity must be greater than zero"):
        process_gate_flow(gates)

def test_gate_flow_validation_missing_fields():
    gates = [
        {
            "gate_id": "Gate A",
            "current_crowd_count": 10,
            "gate_capacity": 1000
            # missing kickoff
        }
    ]
    with pytest.raises(ValueError, match="Missing required field: 'time_to_kickoff_minutes'"):
        process_gate_flow(gates)
