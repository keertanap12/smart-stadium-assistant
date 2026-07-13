def allocate_parking(lots, batches):
    """
    Simulates allocation of incoming vehicle batches to parking lots.
    
    Input:
      lots (list of dict): Parking lots, each containing:
        - lot_id (str)
        - lot_capacity (int)
        - current_occupancy (int)
        - is_overflow (bool, optional, defaults to False)
      batches (list of dict): Incoming vehicle batches, each containing:
        - batch_id (str)
        - vehicle_type (str, 'car' or 'bus')
        - count (int)
        - expected_arrival_time (str)
        
    Output:
      dict: Contains:
        - allocations (list of dict): Assignment details per vehicle batch.
        - lots_after_allocation (list of dict): Estimated parking lots states after allocation.
        - recommendation (str): Overall action (e.g. "Open overflow lot").
    """
    if not isinstance(lots, list) or not isinstance(batches, list):
        raise TypeError("Input 'lots' and 'batches' must be lists.")
        
    # Input Validation & Deep Copying to avoid side effects
    lots_state = []
    for lot in lots:
        if not isinstance(lot, dict):
            raise TypeError("Each parking lot must be a dictionary.")
        required_fields = ['lot_id', 'lot_capacity', 'current_occupancy']
        for field in required_fields:
            if field not in lot:
                raise ValueError(f"Missing required field in lot: '{field}'")
                
        try:
            capacity = int(lot['lot_capacity'])
            occupancy = int(lot['current_occupancy'])
        except (ValueError, TypeError):
            raise ValueError(f"Lot capacity and occupancy must be valid numbers.")
            
        if capacity <= 0:
            raise ValueError(f"Lot {lot.get('lot_id')}: Capacity must be greater than zero ({capacity}).")
        if occupancy < 0:
            raise ValueError(f"Lot {lot.get('lot_id')}: Occupancy cannot be negative ({occupancy}).")
        if occupancy > capacity:
            raise ValueError(f"Lot {lot.get('lot_id')}: Current occupancy ({occupancy}) cannot exceed capacity ({capacity}).")
            
        lots_state.append({
            "lot_id": str(lot['lot_id']),
            "lot_capacity": capacity,
            "current_occupancy": occupancy,
            "is_overflow": bool(lot.get('is_overflow', False))
        })
        
    validated_batches = []
    for batch in batches:
        if not isinstance(batch, dict):
            raise TypeError("Each vehicle batch must be a dictionary.")
        required_fields = ['batch_id', 'vehicle_type', 'count', 'expected_arrival_time']
        for field in required_fields:
            if field not in batch:
                raise ValueError(f"Missing required field in batch: '{field}'")
                
        vehicle_type = str(batch['vehicle_type']).lower()
        if vehicle_type not in ['car', 'bus']:
            raise ValueError(f"Vehicle type must be either 'car' or 'bus', got '{vehicle_type}'.")
            
        try:
            count = int(batch['count'])
        except (ValueError, TypeError):
            raise ValueError("Vehicle count must be a valid number.")
            
        if count <= 0:
            raise ValueError(f"Batch {batch.get('batch_id')}: Vehicle count must be greater than zero ({count}).")
            
        validated_batches.append({
            "batch_id": str(batch['batch_id']),
            "vehicle_type": vehicle_type,
            "count": count,
            "expected_arrival_time": str(batch['expected_arrival_time'])
        })
        
    allocations = []
    
    # Process allocations sequentially
    for batch in validated_batches:
        v_type = batch['vehicle_type']
        count = batch['count']
        
        best_lot = None
        max_free = -1
        
        for lot in lots_state:
            # We skip overflow lots for normal auto-allocation if they aren't active yet.
            # Or we can assign to them if they are in the list. The requirement says:
            # "If all main lots are projected to exceed 90% occupancy -> recommendation = 'Open overflow lot'".
            # So overflow lots should be kept as reserves. Let's only allocate to non-overflow lots initially,
            # unless no non-overflow lot has space, in which case we might check overflow lots, or we don't
            # allocate to overflow lots at all and just output the alert and overflow recommendation.
            # Let's check: "Assign each incoming batch to the lot with the most free capacity.
            # Buses need to be assigned to lots with at least 5 free spaces reserved for bus-sized parking...
            # If all main lots are projected to exceed 90% occupancy after allocation -> recommendation = 'Open overflow lot'"
            # To be clear, we should try to assign to all eligible lots, but we separate "main lots" for the 90% recommendation.
            # Let's allocate to main (non-overflow) lots first. If a lot is marked is_overflow=True, we exclude it
            # from standard allocation unless the overflow lot has been "opened". Let's assume standard allocation only
            # uses main (non-overflow) lots to see if they exceed 90%.
            # Let's implement this: we only allocate batches to main lots (is_overflow == False).
            if lot['is_overflow']:
                continue
                
            free_space = lot['lot_capacity'] - lot['current_occupancy']
            
            # Constraint checks
            if v_type == 'bus':
                # Buses need at least 5 free spaces reserved for bus-sized parking
                if free_space < 5:
                    continue
            
            # Can the lot fit the batch?
            if free_space < count:
                continue
                
            # Pick lot with the most free capacity
            if free_space > max_free:
                max_free = free_space
                best_lot = lot
                
        # Apply allocation
        alert = "None"
        if best_lot:
            best_lot['current_occupancy'] += count
            fill_pct = best_lot['current_occupancy'] / best_lot['lot_capacity']
            assigned_lot_id = best_lot['lot_id']
            
            if fill_pct > 0.90:
                alert = f"Occupancy Alert (>90%): Lot filled to {fill_pct:.1%}"
        else:
            assigned_lot_id = "Unassigned"
            fill_pct = 0.0
            alert = "Allocation Failed: Insufficient space or bus parking buffer violated"
            
        allocations.append({
            "batch_id": batch['batch_id'],
            "vehicle_type": v_type,
            "count": count,
            "expected_arrival_time": batch['expected_arrival_time'],
            "assigned_lot": assigned_lot_id,
            "fill_percentage_after": fill_pct,
            "alert": alert
        })
        
    # Recommendation logic: "If all main lots are projected to exceed 90% occupancy after allocation -> recommendation = 'Open overflow lot'"
    main_lots = [l for l in lots_state if not l['is_overflow']]
    
    # Check if all main lots exceed 90% occupancy
    # If there are no main lots, default to false
    all_main_exceed_90 = len(main_lots) > 0
    for lot in main_lots:
        fill_pct = lot['current_occupancy'] / lot['lot_capacity']
        if fill_pct <= 0.90:
            all_main_exceed_90 = False
            break
            
    recommendation = "No action needed"
    if all_main_exceed_90:
        recommendation = "Open overflow lot"
        
    return {
        "allocations": allocations,
        "lots_after_allocation": lots_state,
        "recommendation": recommendation
    }
