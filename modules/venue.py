ALLOWED_VENUE_TYPES = [
    "Cricket Stadium",
    "Football Stadium",
    "Shopping Mall",
    "Open Market/Bazaar",
    "Other"
]

def validate_venue_inputs(name, venue_type, city):
    """
    Validates venue input fields.
    
    Returns:
      (bool, str): (is_valid, error_message)
    """
    if not name or not str(name).strip():
        return False, "Venue Name is required and cannot be empty."
        
    if not venue_type or not str(venue_type).strip():
        return False, "Venue Type is required."
        
    if not city or not str(city).strip():
        return False, "Location/City is required and cannot be empty."
        
    venue_type_str = str(venue_type).strip()
    if venue_type_str not in ALLOWED_VENUE_TYPES:
        return False, f"Invalid Venue Type. Must be one of: {', '.join(ALLOWED_VENUE_TYPES)}"
        
    return True, ""
