from marshmallow import Schema, fields, validate, RAISE


class RestaurantCreateSchema(Schema):
    class Meta:
        unknown = RAISE

    name = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    address = fields.Str(required=True, validate=validate.Length(min=5, max=512))
    phone = fields.Str(required=True, validate=validate.Length(min=7, max=20))
    opening_hours = fields.Dict(load_default=dict)
    is_active = fields.Bool(load_default=True)


class RestaurantUpdateSchema(Schema):
    class Meta:
        unknown = RAISE

    name = fields.Str(validate=validate.Length(min=2, max=255))
    address = fields.Str(validate=validate.Length(min=5, max=512))
    phone = fields.Str(validate=validate.Length(min=7, max=20))
    opening_hours = fields.Dict()
    is_active = fields.Bool()


class RestaurantSchema(Schema):
    id = fields.Str(dump_only=True)
    name = fields.Str()
    address = fields.Str()
    phone = fields.Str()
    opening_hours = fields.Dict()
    is_active = fields.Bool()
    created_at = fields.DateTime(dump_only=True)
