# Quick Start Guide

## 1. Setup Environment

Create `.env` file:
```bash
OPENAI_API_KEY=sk-your-openai-key-here
SECRET_KEY=change-this-to-random-string-min-32-chars
DB_USER=finance_user
DB_PASSWORD=finance_pass
DB_NAME=finance_db
```

## 2. Start Services

```bash
docker-compose up --build
```

Wait for both services to be healthy (about 30 seconds).

## 3. Create Users

In a new terminal:
```bash
docker-compose exec web python create_users.py
```

Or use the interactive script:
```bash
docker-compose exec web python -m app.db.init_db
```

Follow prompts to create 2 users (husband & wife) with 6-digit PINs.

## 4. Access Application

Open browser: http://localhost:8000

Login with username and PIN you created.

## 5. Add Your First Transaction

Click "Tambah Transaksi" and try:
- "Terima gaji 5 juta"
- "Beli susu bayi 135 ribu"
- "Bayar listrik 200 ribu"

The AI will automatically classify it!

## Troubleshooting

**Database connection error?**
- Wait a bit longer for PostgreSQL to start
- Check docker-compose logs: `docker-compose logs db`

**OpenAI API error?**
- Verify your API key in `.env`
- Check API credits/balance

**Can't login?**
- Make sure you created users first
- PIN must be exactly 6 digits

## Stopping the Application

```bash
docker-compose down
```

To remove all data:
```bash
docker-compose down -v
```

