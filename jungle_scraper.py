

import csv
import logging
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class WelcomeToJungleScraper:
  
    
    def __init__(self):
        self.base_url = "https://www.welcometothejungle.com/en/jobs?refinementList%5Boffices.country_code%5D%5B%5D=US"
        self.driver = None
        self.jobs = []
        self.wait_time = 20
    
    def setup_driver(self):
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            
            logger.info("Chrome WebDriver initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def close_disclaimer(self):
       
        try:
            logger.info("Step 1: Looking for disclaimer popup...")
            wait = WebDriverWait(self.driver, 10)
            
            # Try multiple selectors for the close button
            close_selectors = [
                "button[aria-label='Close']",
                "button.sc-1t2ha09-0",
                "button[data-testid='modal-close']",
                "button:contains('Close')",
                ".modal button",
                "[class*='close']"
            ]
            
            for selector in close_selectors:
                try:
                    close_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    close_button.click()
                    logger.info("✓ Disclaimer popup closed")
                    time.sleep(2)
                    return True
                except:
                    continue
            
            logger.info("No disclaimer popup found or already closed")
            return True
            
        except Exception as e:
            logger.warning(f"Could not close disclaimer: {e}")
            return True  # Continue anyway
    
    def click_search_bar(self):
        
        try:
            logger.info("Step 2: Clicking search bar...")
            wait = WebDriverWait(self.driver, self.wait_time)
            
            # Try multiple selectors for search input
            search_selectors = [
                "input[placeholder*='search' i]",
                "input[type='search']",
                "input[name='query']",
                "input.ais-SearchBox-input",
                "[data-testid='search-input']"
            ]
            
            for selector in search_selectors:
                try:
                    search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    search_input.click()
                    logger.info("✓ Search bar clicked")
                    time.sleep(1)
                    return search_input
                except:
                    continue
            
            raise Exception("Could not find search bar")
            
        except Exception as e:
            logger.error(f"Failed to click search bar: {e}")
            return None
    
    def search_business(self, search_input):
       
        try:
            logger.info("Step 3: Entering 'Business' in search bar...")
            search_input.clear()
            search_input.send_keys("Business")
            time.sleep(1)
            search_input.send_keys(Keys.RETURN)
            logger.info("✓ Search submitted for 'Business'")
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return False
    
    def wait_for_results(self):
        
        try:
            logger.info("Step 4: Waiting for results to load...")
            wait = WebDriverWait(self.driver, self.wait_time)
            
            # Wait for job cards to appear
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid*='job'], [class*='job-card'], article, .sc-")))
            time.sleep(2)
            
            logger.info("✓ Results loaded")
            return True
            
        except Exception as e:
            logger.error(f"Results did not load: {e}")
            return False
    
    def clean_employee_count(self, text):
        
        if not text:
            return ""
        
        match = re.search(r'(\d+)\s*(?:employee|Employee)', text)
        if match:
            return match.group(1)
        return text.strip()
    
    def clean_posted_time(self, text):
       
        if not text:
            return ""
        
        text = text.strip().lower()
        if text == 'yesterday':
            return '1 days ago'
        return text
    
    def extract_job_data(self, job_card):
        
        try:
            job = {
                'Job_Title': '',
                'Company_Title': '',
                'Company_Slogan': '',
                'Job_Type': '',
                'Location': '',
                'Work_Location': '',
                'Industry': '',
                'Employes_Count': '',
                'Posted_Ago': '',
                'Job_Link': ''
            }
            
          
            card_text = job_card.text
            if not card_text:
                return None
                
            text_lines = [line.strip() for line in card_text.split('\n') if line.strip()]
            
            
            try:
                link_elem = job_card.find_element(By.CSS_SELECTOR, "a[href]")
                href = link_elem.get_attribute('href')
                if href:
                    job['Job_Link'] = href if href.startswith('http') else f"https://www.welcometothejungle.com{href}"
            except:
                pass
            
            if not job['Job_Link']:
                return None  # Skip if no link
            
            
            for i, line in enumerate(text_lines):
                line_lower = line.lower()
                
              
                if not job['Job_Title'] and i == 0:
                    job['Job_Title'] = line
                
             
                elif not job['Company_Title'] and i == 1:
                    job['Company_Title'] = line
                
               
                elif 'employee' in line_lower and not job['Employes_Count']:
                    job['Employes_Count'] = self.clean_employee_count(line)
                
                
                elif any(k in line_lower for k in ['ago', 'yesterday', 'today']) and not job['Posted_Ago']:
                    job['Posted_Ago'] = self.clean_posted_time(line)
                
               
                elif any(k in line_lower for k in ['permanent', 'contract', 'internship', 'temporary']) and not job['Job_Type']:
                    job['Job_Type'] = line
                
                
                elif any(k in line_lower for k in ['remote', 'hybrid', 'on-site']) and not job['Work_Location']:
                    job['Work_Location'] = line
                
              
                elif any(k in line for k in ['New York', 'California', 'Texas', 'USA', 'United States']) and not job['Location']:
                    job['Location'] = line
            
            return job
            
        except Exception as e:
            return None
    
    def scroll_and_collect(self):
       
        try:
            logger.info("Step 5: Collecting job data...")
            
            processed_urls = set()
            scroll_attempts = 0
            max_scrolls = 20
            no_new_jobs_count = 0
            
            while scroll_attempts < max_scrolls and no_new_jobs_count < 3:
                
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, "article, [data-testid*='job'], [class*='job-card']")
                
                if not job_cards:
                    logger.warning("No job cards found")
                    break
                
                initial_count = len(self.jobs)
                
              
                for i, card in enumerate(job_cards):
                    if i % 20 == 0:
                        logger.info(f"Processing jobs... {i}/{len(job_cards)}")
                    
                    job = self.extract_job_data(card)
                    if job and job['Job_Link'] and job['Job_Link'] not in processed_urls:
                        processed_urls.add(job['Job_Link'])
                        self.jobs.append(job)
                
                new_jobs = len(self.jobs) - initial_count
                logger.info(f"Page {scroll_attempts + 1}: Found {new_jobs} new jobs (Total: {len(self.jobs)})")
                
                if new_jobs == 0:
                    no_new_jobs_count += 1
                else:
                    no_new_jobs_count = 0
                
               
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                scroll_attempts += 1
            
            logger.info(f"✓ Collected {len(self.jobs)} unique jobs")
            return True
            
        except Exception as e:
            logger.error(f"Error during scrolling: {e}")
            logger.info(f"Continuing with {len(self.jobs)} jobs collected so far")
            return len(self.jobs) > 0
    
    def save_to_csv(self, filename="results.csv"):
       
        try:
            if not self.jobs:
                logger.warning("No jobs to save")
                return
            
            headers = [
                'Job_Title',
                'Company_Title',
                'Company_Slogan',
                'Job_Type',
                'Location',
                'Work_Location',
                'Industry',
                'Employes_Count',
                'Posted_Ago',
                'Job_Link'
            ]
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for job in self.jobs:
                    row = {header: job.get(header, '') for header in headers}
                    writer.writerow(row)
            
            logger.info(f"✓ Saved {len(self.jobs)} jobs to {filename}")
            print(f"\n✓ CSV file created: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
    
    def answer_questions(self):
        print("\n" + "="*60)
        print("ANSWERS TO QUESTIONS")
        print("="*60)
        
        
        import pandas as pd
        df = pd.read_csv('results.csv')
        
        
        total_jobs = len(df)
        print(f"\n(a) How many total jobs are there?")
        print(f"    Answer: {total_jobs}")
        
        
        ny_jobs = len(df[df['Location'].str.contains('New York', case=False, na=False)])
        print(f"\n(b) How many total jobs are there in New York?")
        print(f"    Answer: {ny_jobs}")
        
        
        df['Employes_Count_Num'] = pd.to_numeric(df['Employes_Count'], errors='coerce')
        more_200 = len(df[df['Employes_Count_Num'] > 200])
        print(f"\n(c) How many companies have more than 200 Employees?")
        print(f"    Answer: {more_200}")
        
        #
        less_200 = len(df[df['Employes_Count_Num'] < 200])
        print(f"\n(d) How many companies have less than 200 Employees?")
        print(f"    Answer: {less_200}")
        
       
        permanent = len(df[df['Job_Type'].str.contains('Permanent', case=False, na=False)])
        print(f"\n(e) How many companies are in job type Permanent Contract?")
        print(f"    Answer: {permanent}")
        
        
        internship = len(df[df['Job_Type'].str.contains('Internship', case=False, na=False)])
        print(f"\n(f) How many companies are in job type Internship?")
        print(f"    Answer: {internship}")
        
        print("\n" + "="*60)
    
    def run(self):
        
        try:
            logger.info("Starting Welcome to the Jungle Job Scraper")
            logger.info(f"Target URL: {self.base_url}")
            
            
            if not self.setup_driver():
                return
            
           
            logger.info(f"Opening URL: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)
            
           
            self.close_disclaimer()
            
           
            search_input = self.click_search_bar()
            if search_input:
                self.search_business(search_input)
            
           
            self.wait_for_results()
            
            
            self.scroll_and_collect()
            
            
        
            self.save_to_csv("results.csv")
            
       
            self.answer_questions()
            
            logger.info("\n" + "="*60)
            logger.info("Scraping completed successfully!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Fatal error in scraping pipeline: {e}")
            raise
        
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")


def main():
    
    scraper = WelcomeToJungleScraper()
    scraper.run()


if __name__ == "__main__":
    main()
