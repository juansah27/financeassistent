"""
CRUD operations for bot reply templates
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.db.models import BotReplyTemplate

def get_all_templates(db: Session, active_only: bool = False) -> List[BotReplyTemplate]:
    """Get all reply templates, optionally filter by active status"""
    query = db.query(BotReplyTemplate)
    if active_only:
        query = query.filter(BotReplyTemplate.is_active == True)
    return query.order_by(BotReplyTemplate.name).all()

def get_default_template(db: Session) -> Optional[BotReplyTemplate]:
    """Get the default active template"""
    return db.query(BotReplyTemplate).filter(
        BotReplyTemplate.is_default == True,
        BotReplyTemplate.is_active == True
    ).first()

def get_template_by_name(db: Session, name: str) -> Optional[BotReplyTemplate]:
    """Get template by name"""
    return db.query(BotReplyTemplate).filter(BotReplyTemplate.name == name).first()

def get_template(db: Session, template_id: int) -> Optional[BotReplyTemplate]:
    """Get template by ID"""
    return db.query(BotReplyTemplate).filter(BotReplyTemplate.id == template_id).first()

def create_template(db: Session, name: str, template: str, is_active: bool = True, is_default: bool = False) -> BotReplyTemplate:
    """Create a new reply template"""
    # If this is set as default, unset other defaults
    if is_default:
        db.query(BotReplyTemplate).filter(BotReplyTemplate.is_default == True).update({"is_default": False})
    
    db_template = BotReplyTemplate(
        name=name,
        template=template,
        is_active=is_active,
        is_default=is_default
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def update_template(
    db: Session, 
    template_id: int, 
    name: str = None, 
    template: str = None, 
    is_active: bool = None,
    is_default: bool = None
) -> Optional[BotReplyTemplate]:
    """Update template"""
    db_template = get_template(db, template_id)
    if not db_template:
        return None
    
    # If setting as default, unset other defaults
    if is_default is True:
        db.query(BotReplyTemplate).filter(
            BotReplyTemplate.is_default == True,
            BotReplyTemplate.id != template_id
        ).update({"is_default": False})
    
    if name is not None:
        db_template.name = name
    if template is not None:
        db_template.template = template
    if is_active is not None:
        db_template.is_active = is_active
    if is_default is not None:
        db_template.is_default = is_default
    
    db.commit()
    db.refresh(db_template)
    return db_template

def delete_template(db: Session, template_id: int) -> bool:
    """Delete template"""
    db_template = get_template(db, template_id)
    if db_template:
        db.delete(db_template)
        db.commit()
        return True
    return False

def format_template(template: str, transaction_id: int, amount: float, category: str, transaction_type: str, raw_input: str = None) -> str:
    """Format template with transaction data"""
    from app.db.models import TransactionType
    
    # Map transaction type to label
    type_labels = {
        TransactionType.EXPENSE: "Pengeluaran",
        TransactionType.INCOME: "Pemasukan",
        TransactionType.SAVING: "Tabungan",
        TransactionType.INVESTMENT: "Investasi",
        TransactionType.DEBT: "Hutang"
    }
    
    # Convert string to enum if needed
    if isinstance(transaction_type, str):
        type_enum = None
        for t in TransactionType:
            if t.value == transaction_type:
                type_enum = t
                break
        type_label = type_labels.get(type_enum, "Transaksi") if type_enum else "Transaksi"
    else:
        type_label = type_labels.get(transaction_type, "Transaksi")
    
    return template.format(
        transaction_id=transaction_id,
        amount=amount,
        amount_formatted=f"Rp {amount:,.0f}".replace(",", "."),
        category=category,
        type=transaction_type.value if hasattr(transaction_type, 'value') else transaction_type,
        type_label=type_label,
        raw_input=raw_input or ""
    )

def format_confirmation_template(template: str, data: dict) -> str:
    """
    Format template for the daily transaction summary.
    Expects data to have: transactions_list, total_today, sisa_budget, insight, total_tx_count, biggest_expense
    """
    return template.format(
        transactions_list=data.get("transactions_list", ""),
        total_today=data.get("total_today", "Rp 0"),
        sisa_budget=data.get("sisa_budget", "Rp 0"),
        insight=data.get("insight", ""),
        total_tx_count=data.get("total_tx_count", 0),
        biggest_expense=data.get("biggest_expense", "-")
    )

def format_recurring_template(template: str, recur_id: int, description: str, amount: float, category: str, interval: str) -> str:
    """Format template for recurring transactions"""
    return template.format(
        id=recur_id,
        description=description,
        amount=amount,
        amount_formatted=f"Rp {amount:,.0f}".replace(",", "."),
        category=category,
        interval=interval
    )

