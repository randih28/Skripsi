import hashlib

def hash_password(password):
    return hashlib.sha1(password.encode()).hexdigest()

def check_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)
