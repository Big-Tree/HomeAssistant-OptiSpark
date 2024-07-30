class DeviceResponse:
    id: int
    name: str
    location_id: int
    manufacturer: str
    model_name: str
    version: str
    integration_type: str
    integration_params: dict

    def __init__(
            self,
            id: int,
            name: str,
            location_id: int,
            manufacturer: str,
            model_name: str,
            version: str,
            integration_type: str,
            integration_params: dict
    ):
        self.id = id
        self.name = name
        self.location_id = location_id
        self.manufacturer = manufacturer
        self.model_name = model_name
        self.version = version
        self.integration_type = integration_type
        self.integration_params = integration_params

    @classmethod
    def from_json(cls, json: dict):
        try:
            return cls(
                id=json["id"],
                name=json["name"],
                location_id=json["locationId"],
                manufacturer=json["manufacturer"],
                model_name=json["modelname"],
                version=json["version"],
                integration_type=json["integrationType"],
                integration_params=json["integrationParams"]
            )
        except:
            return None
