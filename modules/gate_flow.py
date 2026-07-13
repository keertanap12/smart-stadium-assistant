def process_gate_flow(gates):
    """
    Processes the crowd flow status and recommendations for all gates.
    
    Input:
      gates (list of dict): A list of dictionaries, each containing:
        - gate_id (str)
        - current_crowd_count (int)
        - gate_capacity (int)
        - time_to_kickoff_minutes (int)
        
    Output:
      list of dict: Gate statuses and operational recommendations.
    """
    if not isinstance(gates, list):
        raise TypeError("Input 'gates' must be a list of dictionaries.")
        
    processed_gates = []
    near_or_critical_count = 0
    
    # First pass: validate inputs, calculate crowd %, assign base status/recommendation
    for gate in gates:
        if not isinstance(gate, dict):
            raise TypeError("Each gate item must be a dictionary.")
            
        required_fields = ['gate_id', 'current_crowd_count', 'gate_capacity', 'time_to_kickoff_minutes']
        for field in required_fields:
            if field not in gate:
                raise ValueError(f"Missing required field: '{field}'")
                
        gate_id = gate['gate_id']
        try:
            current_crowd_count = int(gate['current_crowd_count'])
            gate_capacity = int(gate['gate_capacity'])
            time_to_kickoff_minutes = int(gate['time_to_kickoff_minutes'])
        except (ValueError, TypeError):
            raise ValueError("Crowd count, capacity, and time to kickoff must be valid numbers.")
            
        if current_crowd_count < 0:
            raise ValueError(f"Gate {gate_id}: Crowd count cannot be negative ({current_crowd_count}).")
        if gate_capacity <= 0:
            raise ValueError(f"Gate {gate_id}: Capacity must be greater than zero ({gate_capacity}).")
        if time_to_kickoff_minutes < 0:
            raise ValueError(f"Gate {gate_id}: Time to kickoff cannot be negative ({time_to_kickoff_minutes}).")
            
        crowd_percentage = current_crowd_count / gate_capacity
        
        if crowd_percentage > 0.95:
            status = "Critical"
            recommendation = "Close gate temporarily, deploy staff"
            near_or_critical_count += 1
        elif crowd_percentage > 0.85:
            status = "Near Capacity"
            recommendation = "Redirect fans to nearest gate under 60% capacity"
            near_or_critical_count += 1
        else:
            status = "Normal"
            recommendation = "No action needed"
            
        processed_gates.append({
            "gate_id": str(gate_id),
            "current_crowd_count": current_crowd_count,
            "gate_capacity": gate_capacity,
            "time_to_kickoff_minutes": time_to_kickoff_minutes,
            "crowd_percentage": crowd_percentage,
            "status": status,
            "recommendation": recommendation
        })
        
    # Second pass: Apply time-to-kickoff overflow rule
    # "If time_to_kickoff_minutes < 30 and multiple gates are 'Near Capacity' or 'Critical' -> add recommendation = 'Open overflow gate'"
    for pg in processed_gates:
        if pg['time_to_kickoff_minutes'] < 30 and near_or_critical_count >= 2:
            if pg['status'] in ["Critical", "Near Capacity"]:
                pg['recommendation'] += " | Open overflow gate"
                
    return processed_gates
