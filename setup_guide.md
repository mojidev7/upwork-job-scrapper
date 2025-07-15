# Upwork Job Scraper Setup Guide

## Prerequisites

1. **Python 3.7+** installed on your system
2. **Google Chrome** browser installed
3. **Active Upwork account** (logged in)
4. **Telegram Bot** and **Channel** set up

## Step-by-Step Setup

### 1. Install Required Packages

```bash
pip install -r requirements.txt
```

### 2. Download ChromeDriver

The script uses Selenium with Chrome. You can either:

**Option A: Use webdriver-manager (Recommended)**
- The script will automatically download the correct ChromeDriver
- No manual setup required

**Option B: Manual ChromeDriver setup**
- Download ChromeDriver from: https://chromedriver.chromium.org/
- Place it in your system PATH or project directory

### 3. Find Your Chrome Profile Path

To use your logged-in Chrome session, you need to find your Chrome profile path:

**Windows:**
```
C:\Users\[YourUsername]\AppData\Local\Google\Chrome\User Data
```

**Mac:**
```
/Users/[YourUsername]/Library/Application Support/Google/Chrome
```

**Linux:**
```
/home/[YourUsername]/.config/google-chrome
```

### 4. Create Telegram Bot

1. Message **@BotFather** on Telegram
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Save the **Bot Token** you receive

### 5. Create Telegram Channel

1. Create a new Telegram channel
2. Add your bot as an administrator to the channel
3. Get your channel ID:
   - For public channels: Use `@channelname`
   - For private channels: Forward a message from the channel to @userinfobot to get the ID

### 6. Configure the Script

Open the Python script and update these variables in the `main()` function:

```python
# Update these values
CHROME_PROFILE_PATH = r"C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHANNEL_ID = "@your_channel_name"  # or "-1001234567890" for private channels

# Customize your search URL
SEARCH_URL = "https://www.upwork.com/nx/search/jobs/?nbs=1&sort=recency"
```

### 7. Test Your Setup

1. **Login to Upwork** in Chrome first
2. **Close all Chrome instances** before running the script
3. Run the script:
   ```bash
   python upwork_scraper.py
   ```

## Customization Options

### Search Filters

You can customize the Upwork search URL to include specific filters:

```python
# Example URLs with filters
SEARCH_URL = "https://www.upwork.com/nx/search/jobs/?nbs=1&sort=recency&q=python"  # Python jobs
SEARCH_URL = "https://www.upwork.com/nx/search/jobs/?nbs=1&sort=recency&contractor_tier=2"  # Intermediate level
SEARCH_URL = "https://www.upwork.com/nx/search/jobs/?nbs=1&sort=recency&hourly_rate_min=25"  # Min $25/hour
```

### Message Formatting

You can modify the `format_job_message()` function to change how jobs appear in Telegram:

- Change emojis
- Add/remove fields
- Modify text formatting
- Adjust message length

### Scraping Frequency

Modify these variables in the script:

```python
MAX_JOBS = 5  # Number of jobs to scrape per run
# In the loop: if i % 2 == 1  # Change to scrape different intervals
```

## Running the Scraper

### Manual Execution
```bash
python upwork_scraper.py
```

### Scheduled Execution (Windows)
Create a batch file and use Windows Task Scheduler:

```batch
@echo off
cd /d "C:\path\to\your\script"
python upwork_scraper.py
```

### Scheduled Execution (Linux/Mac)
Use cron:

```bash
# Run every 30 minutes
*/30 * * * * /usr/bin/python3 /path/to/upwork_scraper.py

# Run every hour
0 * * * * /usr/bin/python3 /path/to/upwork_scraper.py
```

## Troubleshooting

### Common Issues

1. **Chrome Profile Error**
   - Ensure Chrome is completely closed before running the script
   - Verify the profile path is correct
   - Try using a fresh Chrome profile

2. **Telegram Sending Failed**
   - Check bot token is correct
   - Ensure bot is added as admin to the channel
   - Verify channel ID format (@username or -1001234567890)

3. **Job Elements Not Found**
   - Upwork may have changed their HTML structure
   - Check browser console for errors
   - Update selectors if needed

4. **Rate Limiting**
   - Increase delays between requests
   - Reduce MAX_JOBS value
   - Add random delays

### Debug Mode

To see what's happening, you can:

1. Remove the `--headless` argument to see the browser
2. Increase logging level:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

## Security Notes

- Keep your Telegram bot token secure
- Don't commit credentials to version control
- Consider using environment variables for sensitive data:

```python
import os
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
```

## Legal Considerations

- Respect Upwork's Terms of Service
- Don't scrape too aggressively (add appropriate delays)
- Consider using Upwork's official API if available
- Be mindful of rate limiting and server load

## Advanced Features

### Database Integration
You can add database functionality to track scraped jobs:

```python
import sqlite3

# Create database to track scraped jobs
conn = sqlite3.connect('upwork_jobs.db')
# Add job tracking logic
```

### Webhook Integration
Instead of polling, you could set up webhooks for real-time updates.

### Multiple Search Queries
Run multiple search queries with different filters.

### Job Filtering
Add custom filters based on keywords, budget ranges, etc.
