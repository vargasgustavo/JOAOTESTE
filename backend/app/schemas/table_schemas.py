from marshmallow import RAISE, Schema, fields, validate


class TableCreateSchema(Schema):
    class Meta:
        unknown = RAISE

    number = fields.Int(required=True, validate=validate.Range(min=1))
    capacity = fields.Int(required=True, validate=validate.Range(min=1, max=50))
    pos_x = fields.Float(load_default=None)
    pos_y = fields.Float(load_default=None)
    status = fields.Str(
        load_default="AVAILABLE",
        validate=validate.OneOf(["AVAILABLE", "RESERVED", "OCCUPIED", "CLEANING"]),
    )


class TableUpdateSchema(Schema):
    class Meta:
        unknown = RAISE

    number = fields.Int(validate=validate.Range(min=1))
    capacity = fields.Int(validate=validate.Range(min=1, max=50))
    pos_x = fields.Float(allow_none=True)
    pos_y = fields.Float(allow_none=True)


class TableSchema(Schema):
    id = fields.Str(dump_only=True)
    restaurant_id = fields.Str()
    number = fields.Int()
    capacity = fields.Int()
    pos_x = fields.Float(allow_none=True)
    pos_y = fields.Float(allow_none=True)
    status = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
