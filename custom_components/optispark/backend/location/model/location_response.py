from custom_components.optispark.const import LOGGER


class LocationResponse:
    id: int
    name: str
    address: str
    zipcode: str
    city: str
    country: str
    tariff_id: int
    tariff_params: dict
    thermostat_id: int

    def __init__(
            self,
            id: int,
            name: str,
            address: str,
            zipcode: str,
            city: str,
            country: str,
            tariff_id: int,
            tariff_params: dict,
            thermostat_id: int,
    ):
        self.id = id
        self.name = name
        self.address = address
        self.zipcode = zipcode
        self.city = city
        self.country = country
        self.tariff_id = tariff_id
        self.tariff_params = tariff_params
        self.thermostat_id = thermostat_id

    @classmethod
    def from_json(cls, json: dict):
        try:
            address = json["address"]
            return cls(
                id=json["id"],
                name=json["name"],
                address=address["address"],
                zipcode=address["zipcode"],
                city=address["city"],
                country=address["country"],
                tariff_id=json["tariffId"],
                tariff_params=json["tariffParams"],
                thermostat_id=json["thermostatId"],
            )
        except KeyError as e:
            LOGGER.error(f"Error: No key in JSON - {e}")
            return None
        except Exception as e:
            LOGGER.error(f"Error: {e}")
            return None
