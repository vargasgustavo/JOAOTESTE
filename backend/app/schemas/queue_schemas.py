from marshmallow import RAISE, Schema, fields, validate


class QueueEntryCreateSchema(Schema):
    class Meta:
        unknown = RAISE

    customer_name = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    customer_phone = fields.Str(required=True, validate=validate.Length(min=7, max=20))
    party_size = fields.Int(required=True, validate=validate.Range(min=1, max=50))


class QueueEntrySchema(Schema):
    id = fields.Str(dump_only=True)
    restaurant_id = fields.Str()
    customer_id = fields.Str(allow_none=True)
    customer_name = fields.Str()
    customer_phone = fields.Method("mask_phone")
    party_size = fields.Int()
    status = fields.Str()
    position = fields.Int(allow_none=True)
    assigned_table_id = fields.Str(allow_none=True)
    joined_at = fields.DateTime(dump_only=True)
    called_at = fields.DateTime(dump_only=True, allow_none=True)
    seated_at = fields.DateTime(dump_only=True, allow_none=True)
    cancelled_at = fields.DateTime(dump_only=True, allow_none=True)
    estimated_wait_minutes = fields.Int(dump_default=None, allow_none=True)

    def mask_phone(self, obj) -> str:
        phone = obj.customer_phone if hasattr(obj, "customer_phone") else obj.get("customer_phone", "")
        return "****" + phone[-4:] if len(phone) >= 4 else "****"
