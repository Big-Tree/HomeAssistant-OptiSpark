class LoginResponse:
    token: str
    token_type: str
    has_locations: bool
    has_devices: bool

    def __init__(self, token: str, token_type: str, has_locations: bool, has_devices: bool):
        self.token = token
        self.token_type = token_type
        self.has_locations = has_locations
        self.has_devices = has_devices
