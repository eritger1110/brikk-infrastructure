# src/schemas/agent.py
from marshmallow import Schema, fields, validate, EXCLUDE

class AgentCreateSchema(Schema):
    # v4: use load_default instead of missing
    name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    description = fields.Str(load_default=None, allow_none=True)

    # Use load_default=list so you get [] when key is absent
    capabilities = fields.List(fields.Str(), load_default=list)
    tags = fields.List(fields.Str(), load_default=list)

    # default to English if not provided
    language = fields.Str(load_default="en")

    class Meta:
        unknown = EXCLUDE
