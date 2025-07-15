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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UpworkJobScraper:
    def __init__(self, chrome_profile_path: str, telegram_bot_token: str, telegram_channel_id: str):
        """
        Initialize the Upwork job scraper
        
        Args:
            chrome_profile_path: Path to your Chrome profile directory
            telegram_bot_token: Your Telegram bot token
            telegram_channel_id: Your Telegram channel ID (e.g., @your_channel or -1001234567890)
        """
        self.chrome_profile_path = chrome_profile_path
        self.telegram_bot_token = telegram_bot_token
        self.telegram_channel_id = telegram_channel_id
        self.driver = None
        self.scraped_jobs = set()  # Track scraped job IDs to avoid duplicates
        
    def setup_driver(self):
        """Setup Chrome driver with existing profile"""
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.chrome_profile_path}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Optional: Run in headless mode (comment out if you want to see the browser)
        # chrome_options.add_argument("--headless")
        
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
                job_data['description'] = desc_element.text.strip()
                # Truncate if too long
                if len(job_data['description']) > 500:
                    job_data['description'] = job_data['description'][:500] + "..."
            except:
                job_data['description'] = 'Description not available'
            
            # Extract skills/tags
            try:
                skill_elements = job_element.find_elements(By.CSS_SELECTOR, '[data-test="TokenClamp"] .air3-token span')
                job_data['skills'] = [skill.text.strip() for skill in skill_elements]
            except:
                job_data['skills'] = []
            
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
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            data = {
                'chat_id': self.telegram_channel_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                logger.info("Message sent to Telegram successfully")
                return True
            else:
                logger.error(f"Failed to send message to Telegram: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False
    
    def scrape_jobs(self, search_url: str, max_jobs: int = 10) -> List[Dict]:
        """
        Scrape jobs from Upwork search results
        
        Args:
            search_url: The Upwork search URL
            max_jobs: Maximum number of jobs to scrape
        """
        try:
            self.setup_driver()
            
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
                            time.sleep(2)
                        
                        # Add delay between scraping jobs
                        time.sleep(1)
            
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
    
    # Configuration - UPDATE THESE VALUES
    CHROME_PROFILE_PATH = r"C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"  # Update this path
    TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather
    TELEGRAM_CHANNEL_ID = "@your_channel_name"  # Your channel username or ID
    
    # Upwork search URL - customize this with your search filters
    SEARCH_URL = "https://www.upwork.com/nx/search/jobs/?nbs=1&sort=recency"
    
    # Maximum jobs to scrape and send per run
    MAX_JOBS = 5
    
    # Initialize scraper
    scraper = UpworkJobScraper(
        chrome_profile_path=CHROME_PROFILE_PATH,
        telegram_bot_token=TELEGRAM_BOT_TOKEN,
        telegram_channel_id=TELEGRAM_CHANNEL_ID
    )
    
    # Run scraper
    jobs = scraper.scrape_jobs(SEARCH_URL, MAX_JOBS)
    
    print(f"Scraping completed. {len(jobs)} jobs processed.")

if __name__ == "__main__":
    main()
