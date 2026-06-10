# HERMES — Finance Assistant Repository

This file is the primary project context for Hermes when working in this repository.

## Profile

- Hermes profile: `finance`
- Repository path: `/home/ladyqiu/projects/financeassistent`
- This profile is dedicated to this repository only.

## Project Overview

Family Finance Assistant is a private family finance management system with:

- FastAPI backend
- PostgreSQL database
- WhatsApp bot using Node.js and Baileys
- Web UI using Jinja2 and Tailwind CSS
- AI-based transaction classification and financial analysis
- Scheduler for recurring transactions, reminders, reports, and backups

## Core Architecture

Main services:

- `finance_db` — PostgreSQL database
- `finance_web` — FastAPI backend
- `finance_whatsapp_bot` — WhatsApp bot service

Main flow:

1. WhatsApp message is received by the Node.js bot.
2. Bot forwards the message to the FastAPI webhook.
3. Backend classifies the message or command.
4. Transaction or command result is stored/read from PostgreSQL.
5. Bot replies back to WhatsApp.

## Important Files

### Backend

- `app/main.py` — FastAPI entry point
- `app/routes/whatsapp.py` — WhatsApp webhook and finance command handling
- `app/routes/transactions.py` — transaction CRUD
- `app/routes/budget.py` — budget management
- `app/routes/qna.py` — finance Q&A
- `app/db/models.py` — SQLAlchemy models
- `app/db/session.py` — database session
- `app/ai/classifier.py` — transaction classifier
- `app/ai/analyst.py` — financial analyst logic
- `app/services/financial_qna.py` — main finance Q&A engine
- `app/services/report_generator.py` — WhatsApp report generator
- `app/services/ocr.py` — receipt/image OCR service
- `app/tasks/scheduler.py` — background jobs

### WhatsApp Bot

- `whatsapp-bot/socket.js` — WhatsApp connection and message routing
- `whatsapp-bot/handlers/message.js` — text message handler
- `whatsapp-bot/handlers/image.js` — image/OCR handler
- `whatsapp-bot/handlers/command.js` — command handler
- `whatsapp-bot/services/api.js` — API client to FastAPI

### Documentation

- `schema.md` — database schema reference
- `SOUL.md` — operational database guide
- `AGENTS.md` — agent rules
- `docs/` — additional project documentation

## Technology Stack

- Backend: Python 3.11, FastAPI, Uvicorn
- Database: PostgreSQL 15
- ORM: SQLAlchemy 2.x
- Frontend: Jinja2, Tailwind CSS, Vanilla JS
- WhatsApp: Node.js, Baileys
- Scheduler: APScheduler
- AI: OpenAI/Gemini-compatible APIs
- Infrastructure: Docker Compose

## Docker Commands

Check containers:

```bash
docker ps
```

Restart all services:

```bash
docker-compose restart
```

Restart backend:

```bash
docker-compose restart web
```

Restart WhatsApp bot:

```bash
docker-compose restart whatsapp-bot
```

View backend logs:

```bash
docker-compose logs -f web
```

View bot logs:

```bash
docker-compose logs -f whatsapp-bot
```

## Database Access

Use this template for direct database queries:

```bash
docker exec finance_db psql -U finance_user -d finance_db -c "SQL_HERE"
```

Always inspect schema before making structural changes.

Main tables:

- `users`
- `accounts`
- `transactions`
- `budgets`
- `recurring_transactions`
- `recurring_income`
- `debts`
- `debt_payments`
- `assets`
- `asset_history`
- `transaction_keywords`
- `user_categories`
- `goals`
- `notifications`
- `whatsapp_report_schedules`
- `whatsapp_groups`

## Database Rules

- Do not use hard delete unless explicitly requested.
- Prefer soft delete using `is_deleted = true`.
- Transaction `amount` must always be positive.
- Transaction direction is determined by `type`.
- Always set `is_deleted = false` for new transactions.
- For `TRANSFER`, use both source and destination account fields.
- Preserve `raw_input` for audit trail when inserting user-originated transactions.
- Enum values must be uppercase.

Important enums:

```text
TransactionType: INCOME, EXPENSE, SAVING, INVESTMENT, DEBT, TRANSFER
AccountType: BANK, EWALLET, CASH, INVESTMENT
DebtType: PERSONAL, BANK, LEASING, CREDIT_CARD, PAYLATER, BILL
AssetType: BPJS, GOLD, PROPERTY, VEHICLE, DEPOSIT, STOCK, CRYPTO
RecurrenceType: DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM
```

## Security Rules

- Do not modify `.env`, credentials, tokens, API keys, or secrets unless explicitly requested.
- Do not print secrets in responses.
- Do not expose private phone numbers, WhatsApp group IDs, or personal identifiers unless explicitly requested.
- Do not modify database backup files unless explicitly requested.
- Be careful with:
  - `.env`
  - `backup/config.yaml`
  - `backup/*.sql.gz`
  - `app/db/models.py`

## Agent Operating Rules

- Work only inside `/home/ladyqiu/projects/financeassistent` unless explicitly instructed.
- Treat this repository as the active project.
- Do not assume context from other repositories.
- Read relevant files before editing.
- Prefer small, focused changes.
- Explain what changed after editing.
- Before changing database models, check whether migration scripts are needed.
- Before changing WhatsApp flow, inspect both bot handler and FastAPI webhook.
- When debugging, check logs before guessing.
- When unsure, inspect files first.

## Recommended Debug Flow

For backend issues:

```bash
docker-compose logs -f web
```

For WhatsApp bot issues:

```bash
docker-compose logs -f whatsapp-bot
```

For database checks:

```bash
docker exec finance_db psql -U finance_user -d finance_db -c "SELECT now();"
```

For current repository:

```bash
pwd
```

Expected:

```bash
/home/ladyqiu/projects/financeassistent
```

## Source of Truth

Use these files as references:

1. `HERMES.md` — active agent context
2. `schema.md` — database schema
3. `SOUL.md` — database operation guide
4. `AGENTS.md` — agent behavior rules
5. `docs/` — detailed documentation
6. actual source code — final source of truth
