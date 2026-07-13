import re
from werkzeug.security import generate_password_hash, check_password_hash

# Regular expression for email validation
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

def validate_signup_inputs(name, email, password):
    """
    Validates user signup details.
    
    Returns:
      (bool, str): (is_valid, error_message)
    """
    if not name or not str(name).strip():
        return False, "Name is required and cannot be empty."
        
    if not email or not str(email).strip():
        return False, "Email is required and cannot be empty."
        
    if not password or not str(password).strip():
        return False, "Password is required and cannot be empty."
        
    email = str(email).strip()
    if not EMAIL_REGEX.match(email):
        return False, "Please enter a valid email address (e.g. user@example.com)."
        
    password = str(password).strip()
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
        
    return True, ""

def hash_password(password):
    """Hashes a plaintext password."""
    return generate_password_hash(password)

def verify_password(stored_hash, password):
    """Verifies a plaintext password against a stored hash."""
    return check_password_hash(stored_hash, password)
