import enum


class UserRole(str, enum.Enum):
    BUYER = "buyer"
    ADMIN = "admin"


class PaymentMethod(str, enum.Enum):
    BANK_QR = "bank_qr"
    COD = "cod"
    ONLINE = "online"


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    UNDER_REVIEW = "under_review"
    PAID = "paid"
    REJECTED = "rejected"
    REFUNDED = "refunded"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"  # COD: awaiting shop confirmation
    PENDING_PAYMENT = "pending_payment"  # QR: awaiting proof submission
    UNDER_REVIEW = "under_review"  # QR: proof submitted, awaiting verification
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


# Order statuses the buyer can cancel from without penalty.
CANCELLABLE_STATUSES = {OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT}


class CatalogStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DiscountType(str, enum.Enum):
    PERCENT = "percent"
    FIXED = "fixed"
