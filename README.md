# AI Psychologist Telegram Bot

A Telegram bot that provides CBT (Cognitive Behavioral Therapy) psychological support using OpenAI GPT models. The bot includes crisis detection, memory management, and session-based conversations.

## Features

✅ **CBT-Based Conversations**: Professional psychological support using cognitive-behavioral therapy approach  
✅ **Crisis Detection**: Automatic risk assessment with specialized crisis mode  
✅ **Memory Management**: Remembers user context across sessions  
✅ **Usage Limits**: Built-in daily message limits  
✅ **Session Management**: Organize conversations into separate sessions  
✅ **PostgreSQL Database**: Persistent storage for all data  

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- OpenAI API key
- Telegram Bot Token (from @BotFather)

## Installation

### 1. Clone or Navigate to Project

```bash
cd /Users/dauletakberdiyev/Desktop/dev/ai_psycholog
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

Create a new PostgreSQL database:

```bash
createdb ai_psycholog
```

Run the database creation script:

```bash
psql -d ai_psycholog -f db/database_creation.sql
```

### 5. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_psycholog
DB_USER=postgres
DB_PASSWORD=your_db_password_here
```

#### Getting Your Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token provided by BotFather
5. Paste it in your `.env` file

## Running the Bot

Start the bot:

```bash
python bot.py
```

You should see:

```
INFO - Starting AI Psychologist Telegram Bot...
INFO - Database pool created: ai_psycholog@localhost
INFO - Prompts loaded successfully
INFO - AI Client initialized with model: gpt-4o-mini
INFO - Bot is running... Press Ctrl+C to stop.
```

## Usage

### User Commands

- `/start` - Register and start using the bot
- `/help` - Show help information
- `/newsession` - Archive current session and start a new one
- `/settings` - View current preferences
- `/stats` - View usage statistics

### Example Conversation

```
User: Привет, у меня сегодня был тяжелый день на работе
Bot: [CBT-based supportive response]

User: Я чувствую, что ничего не получается
Bot: [Helps identify cognitive distortions and provides coping strategies]
```

## Project Structure

```
ai_psycholog/
├── bot.py                  # Main entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── .env                   # Your secrets (not in git)
│
├── db/
│   ├── database.py        # Database connection pool
│   ├── models.py          # Repository pattern for all tables
│   └── database_creation.sql  # Database schema
│
├── ai/
│   ├── client.py          # OpenAI API client
│   ├── prompts.py         # Prompt management
│   ├── detector.py        # Risk detection system
│   └── memory.py          # Memory management
│
├── handlers/
│   ├── commands.py        # Command handlers (/start, /help, etc.)
│   └── conversation.py    # Message conversation handler
│
├── utils/
│   └── logger.py          # Logging configuration
│
└── prompts (*.md files):
    ├── system_promt.md
    ├── crisis_prompt.md
    ├── detector_prompt.md
    ├── memory_summary_prompt.md
    ├── memory_fact_extractor.md
    └── memory_insert_prompt.md
```

## Configuration Options

Edit `.env` to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_MODEL` | GPT model to use | `gpt-4o-mini` |
| `OPENAI_MAX_TOKENS` | Max tokens per response | `1500` |
| `OPENAI_TEMPERATURE` | Response creativity (0-1) | `0.7` |
| `DAILY_MESSAGE_LIMIT` | Messages per day for free users | `20` |
| `SESSION_TIMEOUT_HOURS` | Auto-archive sessions after | `24` |
| `MEMORY_SUMMARY_EVERY_N_MESSAGES` | Create summary every N messages | `10` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## Database Schema

The bot uses the following main tables:

- **users** - User profiles and Telegram info
- **sessions** - Conversation sessions
- **messages** - All messages (user + assistant)
- **risk_events** - Crisis detection logs
- **memory_summaries** - Session summaries
- **memory_facts** - Long-term user facts
- **usage_limits** - Daily message quotas
- **llm_requests** - API usage logs

## Troubleshooting

### Database Connection Errors

```bash
# Check PostgreSQL is running
pg_isready

# Verify database exists
psql -l | grep ai_psycholog
```

### Missing Environment Variables

The bot will show exactly which variables are missing:

```
❌ Configuration Error!
Missing required environment variables:
  - TELEGRAM_BOT_TOKEN
  - OPENAI_API_KEY
```

### API Errors

Check logs in `logs/bot.log` for detailed error messages.

## Security Notes

⚠️ **Never commit your `.env` file!**  
⚠️ Keep your OpenAI API key and bot token secure  
⚠️ Use environment variables in production  

## Contributing

This is an MVP. Future enhancements could include:

- Subscription payments (Telegram Stars, Stripe)
- Multi-language support
- Voice message processing
- Web dashboard for analytics
- Advanced user settings UI

## License

Private project. All rights reserved.

## Support

For issues or questions, contact the project maintainer.
