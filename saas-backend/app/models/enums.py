import enum


class RoleEnum(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"
    SALESPERSON = "salesperson"
    RECEPTIONIST = "receptionist"


class MemberStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class RiskLevel(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class CheckinSource(str, enum.Enum):
    TURNSTILE = "turnstile"
    MANUAL = "manual"
    IMPORT = "import"


class LeadStage(str, enum.Enum):
    NEW = "new"
    CONTACT = "contact"
    VISIT = "visit"
    TRIAL = "trial"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    CANCELLED = "cancelled"


class NPSSentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class NPSTrigger(str, enum.Enum):
    AFTER_SIGNUP_7D = "after_signup_7d"
    MONTHLY = "monthly"
    YELLOW_RISK = "yellow_risk"
    POST_CANCELLATION = "post_cancellation"
