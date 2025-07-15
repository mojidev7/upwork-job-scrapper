import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import os
from typing import List, Dict, Optional
from pathlib import Path
import configparser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UpworkJobScraper:
    def __init__(self, config_file: str = "config.ini"):
        """
        Initialize the Upwork job scraper with config file support
        
        Args:
            config_file: Path to configuration file
        """
        self.config = self.load_config(config_file)
        self.driver = None
        self.scraped_jobs = set()  # Track scraped job IDs to avoid duplicates
        
        # Load scraped jobs from file to persist between runs
        self.load_scraped_jobs()
        
    def load_config(self, config_file: str) -> configparser.ConfigParser:
        """Load configuration from file or environment variables"""
        config = configparser.ConfigParser()
        
        # Default configuration
        config['DEFAULT'] = {
            'chrome_profile_path': '',
            'telegram_bot_token': '',
            'telegram_channel_id': '',
            'search_url': 'https://www.upwork.com/nx/search/jobs/?nbs=1&sort=recency',
            'max_jobs': '5',
            'delay_between_jobs': '2',
            'delay_between_messages': '3',
            'headless': 'false',
            'job_description_max_length': '500'
        }
        
        # Try to read from config file
        if os.path.exists(config_file):
            config.read(config_file)
            logger.info(f"Configuration loaded from {config_file}")
        else:
            logger.info("Config file not found, creating default config.ini")
            self.create_default_config(config_file)
        
        # Override with environment variables if they exist
        env_mapping = {
            'CHROME_PROFILE_PATH': ('DEFAULT', 'chrome_profile_path'),
            'TELEGRAM_BOT_TOKEN': ('DEFAULT', 'telegram_bot_token'),
            'TELEGRAM_CHANNEL_ID': ('DEFAULT', 'telegram_channel_id'),
            'UPWORK_SEARCH_URL': ('DEFAULT', 'search_url'),
            'MAX_JOBS': ('DEFAULT', 'max_jobs'),
        }
        
        for env_var, (section, key) in env_mapping.items():
            if os.getenv(env_var):
                config[section][key] = os.getenv(env_var)
                logger.info(f"Using environment variable {env_var}")
        
        return config
    
    def create_default_config(self, config_file: str):
        """Create a default configuration file"""
        config_content = """[DEFAULT]
# Chrome profile path - update this to your Chrome profile directory
chrome_profile_path = C:\\Users\\YourUsername\\AppData\\Local\\Google\\Chrome\\User Data

# Telegram configuration - get these from @BotFather
telegram_bot_token = YOUR_BOT_TOKEN_HERE
telegram_channel_id = @your_channel_name

# Upwork search URL - customize with your filters
search_url = https://www.upwork.com/nx/search/jobs/?nbs=1&sort=recency

# Scraping settings
max_jobs = 5
delay_between_jobs = 2
delay_between_messages = 3
headless = false
job_description_max_length = 500

[FILTERS]
# Additional search filters (optional)
# Add your custom search parameters here
# Example: min_hourly_rate = 25
# Example: skills = python,django,react
"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Default configuration file created: {config_file}")
        logger.info("Please update the configuration file with your settings.")
    
    def load_scraped_jobs(self):
        """Load previously scraped job IDs from file"""
        scraped_jobs_file = "scraped_jobs.json"
        if os.path.exists(scraped_jobs_file):
            try:
                with open(scraped_jobs_file, 'r') as f:
                    scraped_jobs_data = json.load(f)
                    self.scraped_jobs = set(scraped_jobs_data.get('job_ids', []))
                logger.info(f"Loaded {len(self.scraped_jobs)} previously scraped job IDs")
            except Exception as e:
                logger.warning(f"Could not load scraped jobs file: {e}")
    
    def save_scraped_jobs(self):
        """Save scraped job IDs to file"""
        scraped_jobs_file = "scraped_jobs.json"
        try:
            scraped_jobs_data = {
                'job_ids': list(self.scraped_jobs),
                'last_updated': datetime.now().isoformat()
            }
            with open(scraped_jobs_file, 'w') as f:
                json.dump(scraped_jobs_data, f, indent=2)
            logger.info(f"Saved {len(self.scraped_jobs)} scraped job IDs")
        except Exception as e:
            logger.error(f"Could not save scraped jobs file: {e}")
        
    def setup_driver(self):
        """Setup Chrome driver with existing profile"""
        chrome_options = Options()
        
        profile_path = self.config['DEFAULT']['chrome_profile_path']
        if profile_path:
            chrome_options.add_argument(f"--user-data-dir={profile_path}")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Headless mode based on config
        if self.config['DEFAULT']['headless'].lower() == 'true':
            chrome_options.add_argument("--headless")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def parse_job_posting(self, job_element) -> Optional[Dict]:
        """Parse a single job posting element and extract relevant information"""
        try:
            job_data = {}
            
            # Extract job ID from data attribute
            job_uid = job_element.get_attribute('data-ev-job-uid')
            if not job_uid:
                return None
                
            job_data['job_id'] = job_uid
            
            # Check if we've already scraped this job
            if job_uid in self.scraped_jobs:
                logger.debug(f"Job {job_uid} already scraped, skipping")
                return None
                
            # Extract job title
            title_element = job_element.find_element(By.CSS_SELECTOR, 'h2.job-tile-title a')
            job_data['title'] = title_element.text.strip()
            job_data['url'] = title_element.get_attribute('href')
            
            # Extract posting time
            try:
                time_element = job_element.find_element(By.CSS_SELECTOR, '[data-test="job-pubilshed-date"] span:last-child')
                job_data['posted'] = time_element.text.strip()
            except:
                job_data['posted'] = 'Time not available'
            
            # Extract budget/rate
            try:
                budget_element = job_element.find_element(By.CSS_SELECTOR, '[data-test="job-type-label"] strong')
                job_data['budget'] = budget_element.text.strip()
            except:
                job_data['budget'] = 'Budget not specified'
            
            # Extract experience level
            try:
                exp_element = job_element.find_element(By.CSS_SELECTOR, '[data-test="experience-level"] strong')
                job_data['experience_level'] = exp_element.text.strip()
            except:
                job_data['experience_level'] = 'Not specified'
            
            # Extract duration
            try:
                duration_element = job_element.find_element(By.CSS_SELECTOR, '[data-test="duration-label"] strong:last-child')
                job_data['duration'] = duration_element.text.strip()
            except:
                job_data['duration'] = 'Not specified'
            
            # Extract location
            try:
                location_element = job_element.find_element(By.CSS_SELECTOR, '[data-test="location"] span:last-child')
                job_data['location'] = location_element.text.strip()
            except:
                job_data['location'] = 'Location not specified'
            
            # Extract client info
            try:
                # Payment verification
                try:
                    job_element.find_element(By.CSS_SELECTOR, '[data-test="payment-verified"]')
                    job_data['payment_verified'] = True
                except:
                    job_data['payment_verified'] = False
                
                # Total spent
                try:
                    spent_element = job_element.find_element(By.CSS_SELECTOR, '[data-test="total-spent"] strong')
                    job_data['client_spent'] = spent_element.text.strip()
                except:
                    job_data['client_spent'] = 'Not available'
                
                # Rating
                try:
                    rating_element = job_element.find_element(By.CSS_SELECTOR, '.air3-rating-value-text')
                    job_data['client_rating'] = rating_element.text.strip()
                except:
                    job_data['client_rating'] = 'No rating'
                    
            except Exception as e:
                logger.warning(f"Could not extract client info: {e}")
            
            # Extract job description
            try:
                desc_element = job_element.find_element(By.CSS_SELECTOR, '[data-test="JobDescription"] p')
                description = desc_element.text.strip()
                
                # Truncate if too long based on config
                max_length = int(self.config['DEFAULT']['job_description_max_length'])
                if len(description) > max_length:
                    description = description[:max_length] + "..."
                
                job_data['description'] = description
            except:
                job_data['description'] = 'Description not available'
            
            # Extract skills/tags
            try:
                skill_elements = job_element.find_elements(By.CSS_SELECTOR, '[data-test="TokenClamp"] .air3-token span')
                job_data['skills'] = [skill.text.strip() for skill in skill_elements]
            except:
                job_data['skills'] = []
            
            # Add timestamp
            job_data['scraped_at'] = datetime.now().isoformat()
            
            self.scraped_jobs.add(job_uid)
            return job_data
            
        except Exception as e:
            logger.error(f"Error parsing job posting: {e}")
            return None
    
    def format_job_message(self, job: Dict) -> str:
        """Format job data into a nice Telegram message"""
        
        # Emojis for better formatting
        emojis = {
            'title': '💼',
            'money': '💰',
            'time': '⏰',
            'location': '📍',
            'experience': '🎯',
            'duration': '📅',
            'client': '👤',
            'skills': '🔧',
            'description': '📝',
            'link': '🔗',
            'verified': '✅',
            'unverified': '❌'
        }
        
        # Build the message
        message_parts = []
        
        # Title and basic info
        message_parts.append(f"{emojis['title']} **{job['title']}**")
        message_parts.append("")
        
        # Budget and time info
        message_parts.append(f"{emojis['money']} **Budget:** {job['budget']}")
        message_parts.append(f"{emojis['time']} **Posted:** {job['posted']}")
        message_parts.append(f"{emojis['experience']} **Level:** {job['experience_level']}")
        message_parts.append(f"{emojis['duration']} **Duration:** {job['duration']}")
        message_parts.append(f"{emojis['location']} **Location:** {job['location']}")
        message_parts.append("")
        
        # Client info
        payment_status = emojis['verified'] if job.get('payment_verified', False) else emojis['unverified']
        message_parts.append(f"{emojis['client']} **Client:** {payment_status} Payment {job['client_spent']} spent, Rating: {job['client_rating']}")
        message_parts.append("")
        
        # Skills
        if job['skills']:
            skills_text = ", ".join(job['skills'][:5])  # Limit to 5 skills
            message_parts.append(f"{emojis['skills']} **Skills:** {skills_text}")
            message_parts.append("")
        
        # Description
        message_parts.append(f"{emojis['description']} **Description:**")
        message_parts.append(job['description'])
        message_parts.append("")
        
        # Link
        if job.get('url'):
            full_url = f"https://www.upwork.com{job['url']}" if job['url'].startswith('/') else job['url']
            message_parts.append(f"{emojis['link']} [View Job]({full_url})")
        
        message_parts.append("")
        message_parts.append("---")
        
        return "\n".join(message_parts)
    
    def send_to_telegram(self, message: str) -> bool:
        """Send message to Telegram channel"""
        try:
            bot_token = self.config['DEFAULT']['telegram_bot_token']
            channel_id = self.config['DEFAULT']['telegram_channel_id']
            
            if not bot_token or not channel_id:
                logger.error("Telegram bot token or channel ID not configured")
                return False
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            
            data = {
                'chat_id': channel_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                logger.info("Message sent to Telegram successfully")
                return True
            else:
                logger.error(f"Failed to send message to Telegram: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False
    
    def scrape_jobs(self) -> List[Dict]:
        """Scrape jobs from Upwork search results based on configuration"""
        try:
            self.setup_driver()
            
            search_url = self.config['DEFAULT']['search_url']
            max_jobs = int(self.config['DEFAULT']['max_jobs'])
            delay_between_jobs = float(self.config['DEFAULT']['delay_between_jobs'])
            delay_between_messages = float(self.config['DEFAULT']['delay_between_messages'])
            
            logger.info(f"Navigating to: {search_url}")
            self.driver.get(search_url)
            
            # Wait for job listings to load
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test="JobTile"]')))
            
            # Scroll to load more jobs
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Find all job tiles
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-test="JobTile"]')
            logger.info(f"Found {len(job_elements)} job postings")
            
            scraped_jobs = []
            jobs_sent = 0
            
            # Process every second job (as requested)
            for i, job_element in enumerate(job_elements):
                if i % 2 == 1:  # Every second job (index 1, 3, 5, etc.)
                    if jobs_sent >= max_jobs:
                        break
                        
                    job_data = self.parse_job_posting(job_element)
                    
                    if job_data:
                        logger.info(f"Scraped job: {job_data['title']}")
                        scraped_jobs.append(job_data)
                        
                        # Format and send to Telegram
                        message = self.format_job_message(job_data)
                        if self.send_to_telegram(message):
                            jobs_sent += 1
                            # Add delay between messages to avoid rate limiting
                            time.sleep(delay_between_messages)
                        
                        # Add delay between scraping jobs
                        time.sleep(delay_between_jobs)
            
            # Save scraped job IDs
            self.save_scraped_jobs()
            
            logger.info(f"Successfully scraped and sent {jobs_sent} jobs")
            return scraped_jobs
            
        except Exception as e:
            logger.error(f"Error scraping jobs: {e}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()

def main():
    """Main function to run the scraper"""
    try:
        # Initialize scraper with config file
        scraper = UpworkJobScraper("config.ini")
        
        # Run scraper
        jobs = scraper.scrape_jobs()
        
        print(f"Scraping completed. {len(jobs)} jobs processed.")
        
        if jobs:
            # Optional: Save jobs to JSON file for record keeping
            output_file = f"scraped_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(jobs, f, indent=2)
            print(f"Job data saved to: {output_file}")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
