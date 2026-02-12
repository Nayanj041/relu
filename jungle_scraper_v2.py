
import logging
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WelcomeToJungleScraper:
    def __init__(self):
        self.driver = None
        self.jobs = []
        self.wait_time = 15
        
    def setup_driver(self):
       
        try:
            logger.info("Setting up Chrome WebDriver...")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(5)
            
            logger.info("✓ WebDriver initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False
    
    def navigate_and_search(self):
       
        try:
            
            logger.info("Step 1: Navigating directly to Business search results...")
            self.driver.get("https://www.welcometothejungle.com/en/jobs?query=Business")
            time.sleep(6)
            logger.info("✓ Page loaded with search results")
            
            
            logger.info("Step 2: Checking for disclaimer popup...")
            try:
                close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[class*='close'], button[aria-label*='close' i], button[data-testid='close']")
                for btn in close_buttons[:3]:
                    try:
                        btn.click()
                        logger.info("✓ Disclaimer closed")
                        time.sleep(1)
                        break
                    except:
                        continue
            except:
                logger.info("✓ No disclaimer found")
            
            time.sleep(2)
            logger.info("✓ Ready to extract jobs")
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def fast_extract_jobs(self):
        
        try:
            logger.info("Step 5: Fast extracting jobs from page source...")
            
            
            time.sleep(3)
            
          
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            
            job_cards = soup.find_all('article') or soup.find_all(attrs={'data-testid': lambda x: x and 'job' in str(x).lower()})
            
            if not job_cards:
                # Try finding by class containing 'job'
                job_cards = soup.find_all(class_=lambda x: x and 'job' in str(x).lower())
            
            logger.info(f"Found {len(job_cards)} job cards in HTML")
            
            for card in job_cards[:100]:  # Limit to first 100
                try:
                    # Get all text from card
                    card_text = card.get_text(separator='\n', strip=True)
                    lines = [l.strip() for l in card_text.split('\n') if l.strip() and len(l.strip()) > 1]
                    
                    if len(lines) < 2:
                        continue
                    
                    
                    job_link = ''
                    link = card.find('a', href=True)
                    if link:
                        href = link['href']
                        job_link = href if href.startswith('http') else f"https://www.welcometothejungle.com{href}"
                    
                    if not job_link:
                        continue
                    
                    
                    job = {
                        'Job_Title': lines[0] if len(lines) > 0 else '',
                        'Company_Title': lines[1] if len(lines) > 1 else '',
                        'Company_Slogan': '',
                        'Job_Type': '',
                        'Location': '',
                        'Work_Location': '',
                        'Industry': '',
                        'Employes_Count': '',
                        'Posted_Ago': '',
                        'Job_Link': job_link
                    }
                    
                    
                    full_text = card_text.lower()
                    
                    for line in lines:
                        line_lower = line.lower()
                        
                     
                        if 'employee' in line_lower and not job['Employes_Count']:
                            match = re.search(r'(\d+)\s*employee', line, re.I)
                            if match:
                                job['Employes_Count'] = match.group(1)
                        
                        
                        if ('ago' in line_lower or 'yesterday' in line_lower) and not job['Posted_Ago']:
                            if 'yesterday' in line_lower:
                                job['Posted_Ago'] = '1 days ago'
                            else:
                                job['Posted_Ago'] = line
                        
                     
                        if any(k in line_lower for k in ['permanent', 'contract', 'internship', 'temporary']) and not job['Job_Type']:
                            job['Job_Type'] = line
                        
                        
                        if any(k in line_lower for k in ['remote', 'hybrid', 'on-site']) and not job['Work_Location']:
                            job['Work_Location'] = line
                        
                        
                        if any(k in line for k in ['New York', 'California', 'Texas', 'Boston', 'Chicago', 'USA']) and not job['Location']:
                            job['Location'] = line
                    
                    self.jobs.append(job)
                    
                except Exception as e:
                    continue
            
            logger.info(f"✓ Extracted {len(self.jobs)} jobs")
            return True
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return False
    
    def save_to_csv(self, filename='results.csv'):
        
        try:
            if not self.jobs:
                logger.warning("No jobs to save")
                return False
            
            df = pd.DataFrame(self.jobs)
            df.to_csv(filename, index=False)
            logger.info(f"✓ Saved {len(self.jobs)} jobs to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
            return False
    
    def answer_questions(self):
      
        try:
            logger.info("\n" + "="*60)
            logger.info("CHALLENGE ANSWERS")
            logger.info("="*60)
            
            if not self.jobs:
                logger.warning("No data to analyze")
                return
            
            df = pd.DataFrame(self.jobs)
            
           
            recent_jobs = df[df['Posted_Ago'].str.contains('hour|today|1 day', case=False, na=False)]
            q1 = len(recent_jobs)
            logger.info(f"\n1. Jobs posted in last 24 hours: {q1}")
            
            
            if len(df) > 0 and 'Company_Title' in df.columns:
                top_company = df['Company_Title'].value_counts().iloc[0:1]
                if len(top_company) > 0:
                    logger.info(f"2. Company with most listings: {top_company.index[0]} ({top_company.values[0]} jobs)")
            
            
            remote_jobs = df[df['Work_Location'].str.contains('remote', case=False, na=False)]
            q3 = len(remote_jobs)
            logger.info(f"3. Remote jobs available: {q3}")
      
            if len(df) > 0 and 'Job_Type' in df.columns:
                job_types = df['Job_Type'].value_counts()
                if len(job_types) > 0:
                    logger.info(f"4. Most common job type: {job_types.index[0]} ({job_types.values[0]} jobs)")
            
         
            if len(df) > 0 and 'Location' in df.columns:
                locations = df[df['Location'] != '']['Location'].value_counts()
                if len(locations) > 0:
                    logger.info(f"5. Location with most openings: {locations.index[0]} ({locations.values[0]} jobs)")
            
            
            total = len(df)
            with_count = len(df[df['Employes_Count'] != ''])
            percentage = (with_count / total * 100) if total > 0 else 0
            logger.info(f"6. Jobs with employee count: {percentage:.1f}% ({with_count}/{total})")
            
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"Failed to answer questions: {e}")
    
    def run(self):
      
        try:
            logger.info("="*60)
            logger.info("WELCOME TO THE JUNGLE JOB SCRAPER")
            logger.info("="*60 + "\n")
            
          
            if not self.setup_driver():
                return False
            
            
            if not self.navigate_and_search():
                return False
            
            if not self.fast_extract_jobs():
                return False
            
           
            if not self.save_to_csv():
                return False
            
           
            self.answer_questions()
            
            logger.info("\n✓ Scraping completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("✓ Browser closed")

if __name__ == "__main__":
    scraper = WelcomeToJungleScraper()
    scraper.run()
