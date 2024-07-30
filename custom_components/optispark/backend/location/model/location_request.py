class LocationRequest:
    name: str
    address: str
    zipcode: str
    city: str
    country: str
    tariff_id: int
    tariff_params: dict

    def __init__(
        self,
        name: str,
        address: str,
        zipcode: str,
        city: str,
        country: str,
        tariff_id: int,
        tariff_params: dict,
    ):
        self.name = name
        self.address = address
        self.zipcode = zipcode
        self.city = city
        self.country = country
        self.tariff_id = tariff_id
        self.tariff_params = tariff_params

    def payload(self) -> dict:
        return {
            "name": self.name,
            "address": {
                "address": self.address,
                "zipcode": self.zipcode,
                "city": self.city,
                "country": self.country,
            },
            "tariffId": self.tariff_id,
            "tariffParams": self.tariff_params,
        }
