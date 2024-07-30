from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    address: str
    city: str
    postcode: str
    country: str

    def __str__(self):
        return f"{self.address}, {self.city}, {self.postcode}, {self.country}"