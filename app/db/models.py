from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, Boolean, ForeignKey, Text, Numeric, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum

class DebtType(enum.Enum):
    PERSONAL = "personal"
    BANK = "bank"
    LEASING = "leasing"
    CREDIT_CARD = "credit_card"
    PAYLATER = "paylater"
    BILL = "bill"

class TransactionType(enum.Enum):
    INCOME = "Pemasukan"
    EXPENSE = "Pengeluaran"
    SAVING = "Tabungan"
    INVESTMENT = "Investasi"
    DEBT = "Hutang"
    TRANSFER = "Transfer"

class AccountType(enum.Enum):
    BANK = "Bank"
    EWALLET = "e-Wallet"
    CASH = "Cash"
    INVESTMENT = "Investasi"
    KREDIT = "Kartu Kredit"



class RecurrenceType(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class RecurringIncomeFrequency(enum.Enum):
    MONTHLY = "monthly"
    # Future: WEEKLY = "weekly", BI_WEEKLY = "bi_weekly"

class RecurringIncomeStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class AssetType(enum.Enum):
    BPJS = "BPJS Ketenagakerjaan"
    GOLD = "Emas"
    PROPERTY = "Properti"
    VEHICLE = "Kendaraan"
    DEPOSIT = "Deposito"
    STOCK = "Saham/Reksadana"
    CRYPTO = "Cryptocurrency"

class TransactionKeyword(Base):
    __tablename__ = "transaction_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, nullable=True)  # Mapped category
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserCategory(Base):
    __tablename__ = "user_categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'income', 'expense'
    icon = Column(String, nullable=True)
    color = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)  # System defaults
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Family(Base):
    __tablename__ = "families"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    join_code = Column(String(10), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    users = relationship("User", back_populates="family")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    pin_hash = Column(String, nullable=False)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    family = relationship("Family", back_populates="users")

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False) # e.g. BCA, GoPay, Dompet Utama
    type = Column(SQLEnum(AccountType), nullable=False)
    balance = Column(Numeric(15, 2), default=0.0)
    credit_limit = Column(Numeric(15, 2), default=0.0)  # For credit card accounts
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    category = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    raw_input = Column(String, nullable=False, server_default="")  # Original natural language input
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    recurring_id = Column(Integer, ForeignKey("recurring_transactions.id"), nullable=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    currency_code = Column(String(3), nullable=False, server_default="IDR")
    amount_in_base_currency = Column(Numeric(15, 2), nullable=True)  # Converted to base currency
    tags = Column(String, nullable=True)  # Comma-separated tags
    notes = Column(Text, nullable=True)  # Additional notes
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    photos = relationship("TransactionPhoto", back_populates="transaction", cascade="all, delete-orphan")
    recurring = relationship("RecurringTransaction", back_populates="transactions")
    edits = relationship("TransactionEdit", cascade="all, delete-orphan")
    ocr_data = relationship("ReceiptOCR", cascade="all, delete-orphan")
    account = relationship("Account", foreign_keys=[account_id])
    destination_account = relationship("Account", foreign_keys=[destination_account_id])

    __table_args__ = (
        Index('idx_transaction_user_created', 'user_id', 'created_at'),
        Index('idx_transaction_user_type_created', 'user_id', 'type', 'created_at'),
    )

class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    category = Column(String, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=True)  # Percentage of income (0-100)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_budget_user_period', 'user_id', 'year', 'month'),
    )

class RecurringIncome(Base):
    """
    Monthly recurring income (salary, business income, passive income, etc.)
    Used for cashflow projection calculations
    """
    __tablename__ = "recurring_income"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g., "Gaji Bulanan", "Sewa Kontrakan"
    amount = Column(Numeric(15, 2), nullable=False)
    category = Column(String, nullable=False)
    frequency = Column(SQLEnum(RecurringIncomeFrequency), nullable=False, default=RecurringIncomeFrequency.MONTHLY)
    status = Column(SQLEnum(RecurringIncomeStatus), nullable=False, default=RecurringIncomeStatus.ACTIVE)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    recurrence_type = Column(SQLEnum(RecurrenceType), nullable=False)
    day_of_month = Column(Integer, nullable=True)  # For monthly: day of month (1-31)
    interval_days = Column(Integer, nullable=True) # For custom: number of days
    next_due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    transactions = relationship("Transaction", back_populates="recurring", foreign_keys="Transaction.recurring_id")
    remaining_occurrences = Column(Integer, nullable=True)
    last_paid_at = Column(DateTime(timezone=True), nullable=True)

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=0.0)
    target_date = Column(DateTime(timezone=True), nullable=True)
    is_achieved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TransactionPhoto(Base):
    __tablename__ = "transaction_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    transaction = relationship("Transaction", back_populates="photos")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)  # 'budget', 'recurring', 'goal', 'reminder'
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Currency(Base):
    __tablename__ = "currencies"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(3), unique=True, nullable=False)  # USD, IDR, etc
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    exchange_rate_to_base = Column(Numeric(18, 6), default=1.0)  # Rate to base currency (IDR)
    is_base = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Owner
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)  # 'ayah', 'ibu', 'anak', etc
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TransactionEdit(Base):
    __tablename__ = "transaction_edits"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    edited_by_user_id = Column(Integer, nullable=False)
    old_amount = Column(Float, nullable=True)
    new_amount = Column(Float, nullable=True)
    old_category = Column(String, nullable=True)
    new_category = Column(String, nullable=True)
    old_description = Column(String, nullable=True)
    new_description = Column(String, nullable=True)
    edit_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReceiptOCR(Base):
    __tablename__ = "receipt_ocr"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    photo_id = Column(Integer, ForeignKey("transaction_photos.id"), nullable=False)
    extracted_text = Column(Text, nullable=True)
    merchant_name = Column(String, nullable=True)
    total_amount = Column(Numeric(15, 2), nullable=True)
    date_detected = Column(DateTime(timezone=True), nullable=True)
    items = Column(Text, nullable=True)  # JSON string of items
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False)
    dark_mode = Column(Boolean, default=False)
    base_currency_code = Column(String(3), default="IDR")
    language = Column(String(10), default="id")
    timezone = Column(String(50), default="Asia/Jakarta")
    start_of_month = Column(Integer, default=1)  # Day of month when budget resets (1-28)
    date_format = Column(String(20), default="DD/MM/YYYY")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BotReplyTemplate(Base):
    __tablename__ = "bot_reply_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "default", "success", "error"
    template = Column(Text, nullable=False)  # Template dengan placeholder: {transaction_id}, {amount}, {category}, {type}
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Hanya satu yang bisa default
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    asset_type = Column(SQLEnum(AssetType), nullable=False, index=True)
    name = Column(String, nullable=False)
    current_value = Column(Numeric(18, 2), nullable=False)
    acquisition_date = Column(DateTime(timezone=True), nullable=True)
    acquisition_value = Column(Numeric(18, 2), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=True)  # For gold, stocks, etc.
    unit = Column(String(50), nullable=True)  # gram, lot, share, etc.
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    history = relationship("AssetHistory", back_populates="asset", cascade="all, delete-orphan")

class AssetHistory(Base):
    __tablename__ = "asset_history"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    old_value = Column(Float, nullable=False)
    new_value = Column(Float, nullable=False)
    updated_by_user_id = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    asset = relationship("Asset", back_populates="history")

class WhatsAppReportSchedule(Base):
    __tablename__ = "whatsapp_report_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    is_enabled = Column(Boolean, default=True)
    report_time = Column(String(5), nullable=False, default="10:00")  # Format: "HH:MM"
    group_name = Column(String, nullable=True)
    group_id = Column(String, nullable=True)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WhatsAppGroup(Base):
    __tablename__ = "whatsapp_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_allowed = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PendingConfirmation(Base):
    __tablename__ = "pending_confirmations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    transaction_id = Column(Integer, nullable=True)  # The manual transaction triggering this
    recurring_id = Column(Integer, nullable=False)   # The recurring schedule to update
    action_type = Column(String, nullable=False, default="update_recurring")
    data = Column(Text, nullable=True)  # JSON string for any extra data
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Debt(Base):
    __tablename__ = "debts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(SQLEnum(DebtType), nullable=False, default=DebtType.PERSONAL)
    creditor = Column(String, nullable=False)  # ABC Bank, Andi, etc.
    name = Column(String, nullable=True)      # Pinjaman Modal, etc.
    total_amount = Column(Numeric(15, 2), nullable=False)
    remaining_amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=True)
    tenor = Column(Integer, nullable=True)     # Number of months
    installment_amount = Column(Numeric(15, 2), nullable=True)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    creditor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    debtor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    payments = relationship("DebtPayment", back_populates="debt", cascade="all, delete-orphan")

class DebtPayment(Base):
    __tablename__ = "debt_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, index=True) # Linked payment transaction
    amount = Column(Numeric(15, 2), nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    debt = relationship("Debt", back_populates="payments")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    item_name = Column(String, nullable=False)
    estimated_price = Column(Numeric(15, 2), nullable=True)
    priority = Column(String, nullable=True)  # HIGH, MEDIUM, LOW
    notes = Column(Text, nullable=True)
    is_achieved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
