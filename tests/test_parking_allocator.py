import pytest
from modules.parking_allocator import allocate_parking

def test_allocate_parking_basic_car():
    lots = [
        {"lot_id": "Lot A", "lot_capacity": 100, "current_occupancy": 50},  # 50 free
        {"lot_id": "Lot B", "lot_capacity": 100, "current_occupancy": 30}   # 70 free
    ]
    batches = [
        {"batch_id": "Batch_01", "vehicle_type": "car", "count": 20, "expected_arrival_time": "18:00"}
    ]
    result = allocate_parking(lots, batches)
    assert len(result["allocations"]) == 1
    # Should assign to Lot B since it has the most free space (70 vs 50)
    assert result["allocations"][0]["assigned_lot"] == "Lot B"
    assert result["allocations"][0]["alert"] == "None"
    assert result["lots_after_allocation"][1]["current_occupancy"] == 50  # 30 + 20

def test_allocate_parking_bus_reservation():
    lots = [
        {"lot_id": "Lot A", "lot_capacity": 10, "current_occupancy": 6},   # 4 free (too small for bus)
        {"lot_id": "Lot B", "lot_capacity": 10, "current_occupancy": 4}    # 6 free (>= 5 free, fits bus)
    ]
    batches = [
        {"batch_id": "Batch_Bus", "vehicle_type": "bus", "count": 2, "expected_arrival_time": "18:00"}
    ]
    result = allocate_parking(lots, batches)
    assert len(result["allocations"]) == 1
    # Even though count=2 would mathematically fit in Lot A (4 free), buses require at least 5 free spaces buffer.
    # So it must be assigned to Lot B.
    assert result["allocations"][0]["assigned_lot"] == "Lot B"
    assert result["lots_after_allocation"][1]["current_occupancy"] == 6

def test_allocate_parking_bus_reservation_fails():
    lots = [
        {"lot_id": "Lot A", "lot_capacity": 10, "current_occupancy": 6},   # 4 free
        {"lot_id": "Lot B", "lot_capacity": 10, "current_occupancy": 7}    # 3 free
    ]
    batches = [
        {"batch_id": "Batch_Bus", "vehicle_type": "bus", "count": 2, "expected_arrival_time": "18:00"}
    ]
    result = allocate_parking(lots, batches)
    assert result["allocations"][0]["assigned_lot"] == "Unassigned"
    assert "buffer violated" in result["allocations"][0]["alert"]

def test_allocate_parking_overflow_recommendation():
    lots = [
        {"lot_id": "Lot A", "lot_capacity": 100, "current_occupancy": 85, "is_overflow": False}, # 15 free
        {"lot_id": "Lot B", "lot_capacity": 100, "current_occupancy": 0, "is_overflow": True}    # Overflow Lot
    ]
    # Adding a batch of 10 cars to Lot A makes it 95/100 (>90%)
    batches = [
        {"batch_id": "Batch_01", "vehicle_type": "car", "count": 10, "expected_arrival_time": "18:00"}
    ]
    result = allocate_parking(lots, batches)
    # The main lot (Lot A) will be 95% full. Since all main lots exceed 90%, it should recommend opening overflow lot.
    assert result["recommendation"] == "Open overflow lot"

def test_allocate_parking_no_overflow_needed():
    lots = [
        {"lot_id": "Lot A", "lot_capacity": 100, "current_occupancy": 50, "is_overflow": False},
        {"lot_id": "Lot B", "lot_capacity": 100, "current_occupancy": 50, "is_overflow": False}
    ]
    batches = [
        {"batch_id": "Batch_01", "vehicle_type": "car", "count": 10, "expected_arrival_time": "18:00"}
    ]
    result = allocate_parking(lots, batches)
    # Total occupancy in Lot A will be 50, Lot B will be 60. Neither exceeds 90%.
    assert result["recommendation"] == "No action needed"

def test_allocate_parking_invalid_vehicle():
    lots = [{"lot_id": "Lot A", "lot_capacity": 100, "current_occupancy": 50}]
    batches = [{"batch_id": "Batch_01", "vehicle_type": "motorcycle", "count": 2, "expected_arrival_time": "18:00"}]
    with pytest.raises(ValueError, match="Vehicle type must be either 'car' or 'bus'"):
        allocate_parking(lots, batches)

def test_allocate_parking_negative_occupancy():
    lots = [{"lot_id": "Lot A", "lot_capacity": 100, "current_occupancy": -5}]
    batches = [{"batch_id": "Batch_01", "vehicle_type": "car", "count": 2, "expected_arrival_time": "18:00"}]
    with pytest.raises(ValueError, match="Occupancy cannot be negative"):
        allocate_parking(lots, batches)

def test_allocate_parking_occupancy_exceeds_capacity():
    lots = [{"lot_id": "Lot A", "lot_capacity": 100, "current_occupancy": 110}]
    batches = [{"batch_id": "Batch_01", "vehicle_type": "car", "count": 2, "expected_arrival_time": "18:00"}]
    with pytest.raises(ValueError, match="Current occupancy .* cannot exceed capacity"):
        allocate_parking(lots, batches)
