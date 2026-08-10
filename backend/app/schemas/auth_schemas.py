from marshmallow import RAISE, Schema, fields, validate


class RegisterSchema(Schema):
    class Meta:
        unknown = RAISE

    name = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    phone = fields.Str(required=True, validate=validate.Length(min=7, max=20))
    email = fields.Email(load_default=None)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128), load_only=True)
    role = fields.Str(
        load_default="CUSTOMER",
        validate=validate.OneOf(["CUSTOMER", "RESTAURANT_ADMIN", "STAFF"]),
    )
    restaurant_id = fields.Str(load_default=None)


class LoginSchema(Schema):
    class Meta:
        unknown = RAISE

    phone = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)


class UserSchema(Schema):
    class Meta:
        unknown = RAISE

    id = fields.Str(dump_only=True)
    name = fields.Str()
    phone = fields.Method("mask_phone")
    email = fields.Method("mask_email")
    role = fields.Str()
    restaurant_id = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)

    def mask_phone(self, obj) -> str:
        phone = obj.phone if hasattr(obj, "phone") else obj.get("phone", "")
        return "****" + phone[-4:] if len(phone) >= 4 else "****"

    def mask_email(self, obj) -> str | None:
        email = obj.email if hasattr(obj, "email") else obj.get("email")
        if not email:
            return None
        domain = email.split("@")[-1] if "@" in email else ""
        return f"***@{domain}"
