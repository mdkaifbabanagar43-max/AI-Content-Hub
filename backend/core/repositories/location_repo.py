from core.models.location import Location
from core.repositories.base_repo import BaseProjectRepository

class LocationRepository(BaseProjectRepository[Location]):
    def __init__(self):
        super().__init__(Location, "locations")
