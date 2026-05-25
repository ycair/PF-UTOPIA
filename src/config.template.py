import os

BOT1_TOKEN = os.getenv("BOT1_TOKEN", "your-bot1-token-here")
BOT2_TOKEN = os.getenv("BOT2_TOKEN", "your-bot2-token-here")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
DB_URL = os.getenv("UTOPIA_DB_URL", "postgresql://localhost:5432/utopia")

STOCK_PRICE_UPDATE_MINUTES = 15
SHOP_PRICE_UPDATE_MINUTES = 30
