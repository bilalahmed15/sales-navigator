from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import csv
import json
from datetime import datetime
from openai import OpenAI

class LeadExtractor:
    def __init__(self, driver, openai_api_key=None):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.client = None
        if openai_api_key:
            self.client = OpenAI(api_key=openai_api_key)
    
    def extract_profile_data(self, url):
        """
        Extract detailed profile data from a LinkedIn profile URL
        """
        try:
            self.driver.get(url)
            time.sleep(4)  # wait for page to load

            headline = ""
            about = ""

            # Extract headline
            try:
                headline_elem = self.driver.find_element(By.XPATH, "/html/body/main/div[1]/div[3]/div/div/div/div/div/section[1]/section[1]/div[1]/div[3]/span")
                headline = headline_elem.text
            except:
                pass

            # Try to expand About section if collapsed
            try:
                expand_btn = self.driver.find_element(By.CLASS_NAME, "button-text")
                expand_btn.click()
                time.sleep(1)
            except:
                pass

            # Extract about section
            try:
                about_elem = self.driver.find_element(By.CLASS_NAME, "_content-width_1dtbsb")
                about = about_elem.text
            except:
                pass

            return {
                "url": url,
                "headline": headline,
                "about": about
            }

        except Exception as e:
            print(f"❌ Error extracting profile data from {url}: {e}")
            return {
                "url": url,
                "headline": "",
                "about": ""
            }
    
    def analyze_profile_with_ai(self, profile_data):
        """
        Analyze profile using GPT-4 and assign relevance score
        """
        if not self.client:
            return profile_data
        
        target_description = """
        We are looking for professionals or companies involved in anti-corrosion protection,
        especially those in shipbuilding, railway, tram, and automotive underbody coatings, 
        high-temperature press shops, forging machinery, outdoor equipment like windmills (esp. splash zones), 
        pipe coatings (for water, oil, underground metal pipes), LSR sealants, glass-to-metal bonding, 
        grease dispensing in machines, electric insulators, barrels, drums, and related industrial environments.
        """

        prompt = f"""
        You are an expert B2B sales assistant.

        Given the LinkedIn profile below, evaluate how well this person or company matches the following client description.

        --- Profile ---
        Headline: {profile_data['headline']}
        About: {profile_data['about']}

        --- Target Client Description ---
        {target_description}

        Please answer the following:
        1. Does this profile align with the target? (YES/NO)
        2. Explain briefly why or why not.
        3. Give a score from 0 to 1 indicating how closely they match (e.g. 0.2 = weak match, 0.9 = strong match).
        Respond in the following JSON format:
        {{"match": "YES or NO", "reason": "...", "score": float}}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )

            content = response.choices[0].message.content
            print(f"🤖 GPT Response for {profile_data['url']}:\n{content}\n")

            parsed = json.loads(content)

            profile_data.update({
                "match": parsed.get("match", "NO"),
                "reason": parsed.get("reason", "").strip(),
                "score": float(parsed.get("score", 0.0))
            })

        except Exception as e:
            print(f"❌ GPT error for {profile_data['url']}: {e}")
            profile_data.update({
                "match": "NO",
                "reason": "AI analysis failed",
                "score": 0.0
            })

        return profile_data
    
    def extract_leads(self, target_count=30, extract_profile_data=True, use_ai_filtering=False):
        """
        Extract LinkedIn leads using pagination approach with optional profile data extraction
        """
        if not self.driver:
            raise Exception("Browser not initialized. Please login first.")
        
        try:
            search_url = "https://www.linkedin.com/sales/search/people?query=(spellCorrectionEnabled%3Atrue%2CrecentSearchParam%3A(id%3A3756865305%2CdoLogHistory%3Atrue)%2Ckeywords%3AAnti-corrosion)&sessionId=p7n9oaNfRVOWg9ReV5K7GA%3D%3D"
            
            print(f"🔍 Navigating to search URL...")
            self.driver.get(search_url)
            
            all_hrefs = set()  # Use set to avoid duplicates
            time.sleep(5)
            
            # Scroll to a specific target div
            try:
                target_div = self.driver.find_element(By.XPATH, "/html/body/main/div[1]/div[2]/div[2]/div[2]/div[4]")
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_div)
                print("✅ Scrolled to the target div.")
            except Exception as e:
                print(f"❌ Failed to locate or scroll to the div: {e}")
            
            time.sleep(5)
            
            # Loop through pages
            while len(all_hrefs) < target_count:
                try:
                    # 1. Find the scrollable container and wait for it to be fully loaded
                    print("🔄 Waiting for page to load...")
                    scroll_container = self.wait.until(EC.presence_of_element_located(
                        (By.CLASS_NAME, "_border-search-results_1igybl")
                    ))
                    
                    # Wait a bit more for the page to fully render
                    time.sleep(3)

                    # 2. Extract hrefs from this page
                    title_elements = scroll_container.find_elements(By.CLASS_NAME, "artdeco-entity-lockup__title")
                    page_hrefs = 0
                    
                    for title in title_elements:
                        if len(all_hrefs) >= target_count:
                            break
                        try:
                            link = title.find_element(By.TAG_NAME, "a")
                            href = link.get_attribute("href")
                            if href:
                                all_hrefs.add(href)
                                page_hrefs += 1
                        except:
                            continue

                    print(f"✅ Collected {len(all_hrefs)} total leads (added {page_hrefs} from this page)")

                    if len(all_hrefs) >= target_count:
                        print(f"🎯 Target count reached: {len(all_hrefs)} leads")
                        break

                    # 3. Check if Next button exists and is clickable
                    try:
                        print("🔍 Looking for Next button...")
                        next_btn = self.wait.until(EC.element_to_be_clickable(
                            (By.CLASS_NAME, "artdeco-pagination__button--next")
                        ))
                        
                        if not next_btn.is_enabled():
                            print("🔚 Reached last page - Next button is disabled.")
                            break
                        
                        # Click Next button
                        print("➡️ Clicking Next button...")
                        next_btn.click()
                        
                        # Wait for page to load properly
                        print("⏳ Waiting for next page to load...")
                        time.sleep(8)  # Increased wait time for page load
                        
                        # Wait for the scroll container to be present on the new page
                        self.wait.until(EC.presence_of_element_located(
                            (By.CLASS_NAME, "_border-search-results_1igybl")
                        ))
                        
                        # Additional wait to ensure page is fully loaded
                        time.sleep(3)
                        
                        print("✅ Next page loaded successfully")
                        
                    except Exception as e:
                        print(f"⚠️ No Next button found or cannot click it: {e}")
                        print("🔚 Stopping extraction - reached end of results")
                        break

                except Exception as e:
                    print(f"⚠️ Page error: {e}")
                    print("🔄 Retrying current page...")
                    time.sleep(5)
                    continue

            # Extract profile data if requested
            profile_data = []
            if extract_profile_data:
                print(f"📊 Extracting profile data for {len(all_hrefs)} leads...")
                for i, href in enumerate(list(all_hrefs)[:target_count]):
                    print(f"🔍 Extracting profile {i+1}/{min(len(all_hrefs), target_count)}: {href}")
                    profile = self.extract_profile_data(href)
                    print(f"📋 Extracted profile data: {profile}")
                    
                    # AI filtering if enabled
                    if use_ai_filtering:
                        profile = self.analyze_profile_with_ai(profile)
                        print(f"🤖 AI analysis result: {profile}")
                    
                    profile_data.append(profile)
                    time.sleep(2)  # Small delay between profile extractions
            else:
                # Just create basic profile data with URLs
                print(f"📋 Creating basic profile data for {len(all_hrefs)} leads...")
                profile_data = [{"url": href, "headline": "", "about": "", "match": "NO", "reason": "", "score": 0.0} 
                              for href in list(all_hrefs)[:target_count]]

            print(f"📊 Final profile data count: {len(profile_data)}")
            if profile_data:
                print(f"📋 Sample profile data: {profile_data[0]}")

            # Sort by relevance score if AI filtering was used
            if use_ai_filtering:
                profile_data.sort(key=lambda x: x.get("score", 0.0), reverse=True)
                # Filter to only include matches
                profile_data = [p for p in profile_data if p.get("match", "").upper() == "YES"]

            # Save to CSV with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_leads_{timestamp}.csv"
            filepath = os.path.join('static', 'exports', filename)
            
            # Ensure exports directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Determine fieldnames based on whether AI filtering was used
            if use_ai_filtering:
                fieldnames = ["url", "headline", "about", "match", "reason", "score"]
            else:
                fieldnames = ["url", "headline", "about"]
            
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # Ensure all rows have the required fields
                for profile in profile_data:
                    row = {}
                    for field in fieldnames:
                        if field in profile:
                            row[field] = profile[field]
                        else:
                            # Set default values for missing fields
                            if field == "match":
                                row[field] = "NO"
                            elif field == "reason":
                                row[field] = ""
                            elif field == "score":
                                row[field] = 0.0
                            else:
                                row[field] = ""
                    writer.writerow(row)

            print(f"✅ Finished. Saved {len(profile_data)} leads to {filename}")
            
            return {
                'success': True,
                'filename': filename,
                'count': len(profile_data),
                'message': f'Successfully extracted {len(profile_data)} leads with profile data'
            }
            
        except Exception as e:
            print(f"❌ Error during lead extraction: {e}")
            return {
                'success': False,
                'error': f'Error during lead extraction: {str(e)}'
            }
    
    def extract_leads_old_method(self):
        """
        Old method using scrolling approach (kept for reference)
        """
        if not self.driver:
            raise Exception("Browser not initialized. Please login first.")
        
        try:
            # First scroll the entire page to load all content
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                # Scroll to bottom of page
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # Break if no more content
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Now scroll the results container
            scroll_container = self.wait.until(EC.presence_of_element_located(
                (By.CLASS_NAME, "_border-search-results_1igybl")
            ))
            
            # Scroll the container to load more results
            last_height = self.driver.execute_script("return arguments[0].scrollHeight", scroll_container)
            while True:
                # Scroll down
                self.driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scroll_container)
                time.sleep(2)  # Wait for content to load
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                
                # Break if no more content
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Find all title elements
            title_elements = scroll_container.find_elements(By.CLASS_NAME, "artdeco-entity-lockup__title")
            
            # Extract hrefs
            hrefs = []
            for title in title_elements:
                try:
                    link = title.find_element(By.TAG_NAME, "a")
                    href = link.get_attribute("href")
                    if href:
                        hrefs.append([href])
                except:
                    continue
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_leads_{timestamp}.csv"
            filepath = os.path.join("static", "exports", filename)
            
            # Ensure exports directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save to CSV
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["LinkedIn Profile URL"])  # Header
                writer.writerows(hrefs)
            
            return {
                'success': True,
                'filename': filename,
                'count': len(hrefs),
                'message': f"✅ Saved {len(hrefs)} links to {filename}"
            }
        except Exception as e:
            print(f"Error extracting leads: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

def read_csv_data(filename):
    """
    Read CSV data from the exports directory
    """
    data = []
    try:
        filepath = os.path.join("static", "exports", filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle both old and new CSV formats
                if 'LinkedIn Profile URL' in row:
                    # Old format - convert to new format
                    data.append({
                        'url': row['LinkedIn Profile URL'],
                        'headline': '',
                        'about': '',
                        'match': 'NO',
                        'reason': '',
                        'score': 0.0
                    })
                else:
                    # New format - ensure all fields are present
                    data.append({
                        'url': row.get('url', ''),
                        'headline': row.get('headline', ''),
                        'about': row.get('about', ''),
                        'match': row.get('match', 'NO'),
                        'reason': row.get('reason', ''),
                        'score': float(row.get('score', 0.0)) if row.get('score') else 0.0
                    })
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
    return data 