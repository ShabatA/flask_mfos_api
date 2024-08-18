from json import JSONEncoder
from decimal import Decimal


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert Decimal instances to strings
            return str(obj)
        # For other types, use the superclass method
        return super(CustomJSONEncoder, self).default(obj)
