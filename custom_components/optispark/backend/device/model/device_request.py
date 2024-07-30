from custom_components.optispark import const


class DeviceRequest:
    name: str
    location_id: int
    manufacturer: str
    model_name: str
    version: str
    integration_type: str
    integration_params: dict

    def __init__(
            self, name: str,
            location_id: int,
            manufacturer: str,
            model_name: str,
            version: str,
            integration_params: dict
    ):
        self.name = name
        self.location_id = location_id
        self.manufacturer = manufacturer
        self.model_name = model_name
        self.version = version
        self.integration_type = const.INTEGRATION_NAME
        self.integration_params = integration_params

    def payload(self) -> dict:
        return {
            "name": self.name,
            "locationId": self.location_id,
            "manufacturer": self.manufacturer,
            "modelname": self.model_name,
            "version": self.version,
            "integrationType": self.integration_type,
            "integrationParams": self.integration_params
        }
