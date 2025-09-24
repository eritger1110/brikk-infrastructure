from marshmallow import Schema, fields, validate

class AgentCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    description = fields.Str(required=False, allow_none=True, validate=validate.Length(max=5000))
    capabilities = fields.List(fields.Raw(), required=False)
    tags = fields.List(fields.Str(validate=validate.Length(max=64)), required=False)
