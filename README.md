# Email Prioritizer

A smart email prioritization system that uses Claude AI to intelligently classify and prioritize incoming emails.

## Features

- Automatically classify emails as high/medium/low priority
- Identify urgency and action items in emails
- Reduce email overwhelm by surfacing important messages
- Learn from user feedback to improve over time
- Cost-optimized through intelligent caching and batching

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, PostgreSQL, Redis
- **Frontend**: React, Tailwind CSS
- **AI**: Claude Sonnet 4.5 via Anthropic API
- **Email**: Gmail API with OAuth 2.0

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Anthropic API key
- Gmail API credentials

## Environment Setup

Create a `.env` file in the backend directory:

```bash
# Anthropic
ANTHROPIC_API_KEY=your_key_here

# Gmail API
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_secret
GMAIL_REDIRECT_URI=http://localhost:8000/auth/callback

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/email_prioritizer

# Redis
REDIS_URL=redis://localhost:6379

# App
SECRET_KEY=your_secret_key
ENVIRONMENT=development
```

## Quick Start

### Using Docker (Recommended)

```bash
docker-compose up --build
```

### Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database:**
```bash
docker-compose up -d postgres redis
python scripts/setup_db.py
```

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

## Performance Targets

- API response time: < 500ms (cached), < 3s (uncached)
- Classification accuracy: > 85% based on user feedback
- Cache hit rate: > 70%
- Cost per 1000 emails: < $0.50

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.