# Family Finance Assistant

A private web application for family financial management with AI-powered natural language transaction processing.

## Features

- 🔐 **Private & Secure**: PIN-based authentication (6 digits)
- 🤖 **AI-Powered**: Natural language transaction input in Indonesian
- 📊 **Dashboard**: Monthly income, expenses, and category breakdown
- 📱 **Mobile-First**: Responsive design optimized for mobile devices
- 🐳 **Docker**: Easy deployment with Docker Compose
- 💬 **WhatsApp Bot**: Automatically read transactions from WhatsApp groups

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: HTML (Jinja2), Tailwind CSS, Vanilla JavaScript
- **AI**: OpenAI API (GPT-3.5-turbo)
- **Infrastructure**: Docker, Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

### Setup

1. **Clone and navigate to the project**:
```bash
cd financeassistent
```

2. **Create `.env` file**:
Create a `.env` file in the root directory with the following content:
```
OPENAI_API_KEY=your-openai-api-key-here
GOOGLE_CLOUD_API_KEY=your-google-cloud-api-key-here
SECRET_KEY=your-random-secret-key-here-change-this
WEBHOOK_SECRET=your-webhook-secret-change-this
DB_USER=finance_user
DB_PASSWORD=finance_pass
DB_NAME=finance_db
```

**Important**: 
- Replace `your-openai-api-key-here` with your actual OpenAI API key (optional, used as fallback)
- Replace `your-google-cloud-api-key-here` with your Google Cloud Vision API key (recommended, has free tier: 1000 requests/month)
- Change `SECRET_KEY` to a random secure string

**OCR Setup:**
- **OCR.Space API** (Recommended - Free, no limit for personal use):
  - Default API key `helloworld` works for free tier (no registration needed)
  - For better performance, get free API key at https://ocr.space/OCRAPI
  - Add to `.env` as `OCR_SPACE_API_KEY` (optional, defaults to `helloworld`)
  - **No billing required, truly free!**

- **Google Cloud Vision API** (Optional - Free tier: 1000 requests/month):
  1. Go to https://console.cloud.google.com/
  2. Create a new project or select existing one
  3. Enable "Cloud Vision API"
  4. **Enable billing** (required even for free tier)
  5. Go to "Credentials" → "Create Credentials" → "API Key"
  6. Copy the API key to `.env` as `GOOGLE_CLOUD_API_KEY`
  
- **OpenAI API** (Optional - Fallback):
  - Used as fallback if other OCR providers fail
  - Requires paid credits (no free tier)

3. **Start the application**:
```bash
docker-compose up --build
```

4. **Initialize database with users**:
```bash
docker-compose exec web python -m app.db.init_db
```

Follow the prompts to create two users (husband & wife) with 6-digit PINs.

5. **Access the application**:
Open your browser and go to: `http://localhost:8000`

## Usage

### Login
- Use the username and 6-digit PIN you created during initialization
- Session expires after 15 minutes

### Adding Transactions
Enter transactions in natural Indonesian language:
- "Terima gaji 5 juta"
- "Beli susu bayi 135 ribu"
- "Bayar listrik 200 ribu"
- "Beli bensin 50 ribu debit"

The AI will automatically:
- Detect income vs expense
- Extract amount (handles: ribu, rb, juta, jt)
- Assign appropriate category
- Create structured transaction

### Categories
- Pemasukan (Income)
- Makan (Food)
- Kebutuhan Bayi (Baby Needs)
- Rumah Tangga (Household)
- Transport
- Tagihan (Bills)
- Tabungan (Savings)
- Hiburan (Entertainment)
- Lain-lain (Others)

## WhatsApp Bot Integration

Bot WhatsApp dapat membaca transaksi dari grup WhatsApp dan otomatis menambahkannya ke aplikasi.

**Setup WhatsApp Bot:**
1. Tambahkan `WEBHOOK_SECRET` ke file `.env`
2. Jalankan `docker-compose up --build`
3. Scan QR code yang muncul di logs: `docker-compose logs whatsapp-bot`
4. Tambahkan bot ke grup WhatsApp
5. Kirim transaksi di grup dengan format natural language

**Contoh pesan transaksi:**
- "Beli susu bayi 135 ribu"
- "Terima gaji 5 juta"
- "Bayar listrik 200 ribu"

Lihat [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) untuk panduan lengkap.

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application
│   ├── auth/                # Authentication (PIN + JWT)
│   ├── ai/                  # AI classifier & analyst
│   ├── db/                  # Database models & CRUD
│   ├── routes/              # API routes
│   │   └── whatsapp.py      # WhatsApp webhook endpoint
│   ├── templates/           # HTML templates (Jinja2)
│   └── static/              # CSS & static files
├── whatsapp-bot/            # WhatsApp bot service (Node.js)
│   ├── bot.js               # Bot logic
│   ├── package.json         # Node.js dependencies
│   └── Dockerfile           # Bot container
├── Dockerfile
├── docker-compose.yml
└── .env                     # Environment variables
```

## Development

### Running locally (without Docker)

1. Install dependencies:
```bash
pip install -r app/requirements.txt
```

2. Set up PostgreSQL database

3. Set environment variables:
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/finance_db
export SECRET_KEY=your-secret-key
export OPENAI_API_KEY=your-api-key
```

4. Run:
```bash
uvicorn app.main:app --reload
```

## Security Notes

- PINs are hashed using bcrypt
- JWT tokens expire after 15 minutes
- Database is only accessible internally (not exposed to host)
- No public registration - users must be created manually

## License

Private family use only.

