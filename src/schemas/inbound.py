# -*- coding: utf-8 -*-
# src/schemas/inbound.py
from marshmallow import Schema, fields


class OrderSchema(Schema):
    supplier_id = fields.String(required=True)
    sku = fields.String(required=True)
    qty = fields.Integer(required=True, strict=True)
    customer_ref = fields.String(load_default=None)
    idempotency_key = fields.String(load_default=None)
