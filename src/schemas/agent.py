from marshmallow import Schema, fields

class AgentCreateSchema(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    capabilities = fields.List(fields.Str(), required=False)
    tags = fields.List(fields.Str(), required=False)
    language = fields.Str(required=False, missing="en")  # <-- add this
