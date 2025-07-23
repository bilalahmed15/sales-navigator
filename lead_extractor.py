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
            first_name = ""
            last_name = ""

            # Extract name from heading
            try:
                name_element = self.driver.find_element(By.CLASS_NAME, "_headingText_e3b563")
                name = name_element.text
                
                # Split the name by spaces
                parts = name.strip().split()
                
                # Extract first and last name
                first_name = parts[0] if parts else ""
                last_name = parts[-1] if len(parts) > 1 else ""
                
                print(f"First Name: {first_name}")
                print(f"Last Name: {last_name}")
            except Exception as e:
                print(f"❌ Error extracting name: {e}")

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
                "first_name": first_name,
                "last_name": last_name,
                "headline": headline,
                "about": about
            }

        except Exception as e:
            print(f"❌ Error extracting profile data from {url}: {e}")
            return {
                "url": url,
                "first_name": "",
                "last_name": "",
                "headline": "",
                "about": ""
            }
    
    def analyze_profile_with_ai(self, profile_data, base_prompt=None):
        """
        Analyze profile using GPT-4 and assign relevance score
        """
        if not self.client:
            return profile_data
        
        target_description = base_prompt.strip() if base_prompt else """
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
    
    def extract_leads_from_url(self, linkedin_url, target_count=30, use_ai_filtering=False, base_prompt=None):
        """
        Extract LinkedIn leads from a specific URL without any filters
        """
        if not self.driver:
            raise Exception("Browser not initialized. Please login first.")
        
        try:
            # Navigate to the provided LinkedIn URL
            print(f"🔍 Navigating to provided LinkedIn URL: {linkedin_url}")
            self.driver.get(linkedin_url)
            time.sleep(5)  # Wait for page to load
            
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
                    
                    # 2. Find the target div using XPath and scroll to it
                    try:
                        target_div = self.driver.find_element(By.XPATH, "/html/body/main/div[1]/div[2]/div[2]/div[2]/div[4]")
                        
                        # Scroll the element into view
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_div)
                        
                        print("✅ Scrolled to the target div.")
                        
                        # Wait for 7 seconds as requested
                        print("⏳ Waiting 7 seconds for page to fully load...")
                        time.sleep(7)
                        
                    except Exception as e:
                        print(f"❌ Failed to locate or scroll to the div: {e}")
                        # Continue anyway, maybe the div structure changed
                        time.sleep(5)

                    # 3. Extract hrefs using the specified approach
                    print("🔍 Extracting hrefs from current page...")
                    
                    # Find the scrollable container again (in case page structure changed)
                    try:
                        scroll_container = self.driver.find_element(By.CLASS_NAME, "_border-search-results_1igybl")
                    except:
                        print("⚠️ Could not find scroll container, trying alternative approach")
                        scroll_container = self.driver
                    
                    # Find all title elements inside that container
                    title_elements = scroll_container.find_elements(By.CLASS_NAME, "artdeco-entity-lockup__title")
                    
                    print(f"📋 Found {len(title_elements)} title elements")
                    
                    # Extract hrefs
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
                                print(f"✅ Added href: {href}")
                        except Exception as e:
                            print(f"⚠️ Error extracting href from title element: {e}")
                            continue

                    print(f"✅ Collected {len(all_hrefs)} total leads (added {page_hrefs} from this page)")

                    if len(all_hrefs) >= target_count:
                        print(f"🎯 Target count reached: {len(all_hrefs)} leads")
                        break

                    # 4. Check if Next button exists and is clickable
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

            # Always extract profile data for all leads
            print(f"📊 Extracting profile data for {len(all_hrefs)} leads...")
            profile_data = []
            for i, href in enumerate(list(all_hrefs)[:target_count]):
                print(f"🔍 Extracting profile {i+1}/{min(len(all_hrefs), target_count)}: {href}")
                profile = self.extract_profile_data(href)
                
                # Add AI analysis if AI filtering is enabled
                if use_ai_filtering and self.client:
                    profile = self.analyze_profile_with_ai(profile, base_prompt)
                else:
                    # Add default values for non-AI filtering
                    profile.update({
                        "match": "NO",
                        "reason": "",
                        "score": 0.0
                    })
                
                profile_data.append(profile)
                time.sleep(2)  # Small delay between profile extractions

            print(f"📊 Final profile data count: {len(profile_data)}")
            if profile_data:
                print(f"📋 Sample profile data: {profile_data[0]}")

            # Save to CSV with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_leads_{timestamp}.csv"
            filepath = os.path.join('static', 'exports', filename)
            
            # Ensure exports directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Determine fieldnames based on whether AI filtering was used
            if use_ai_filtering and self.client:
                fieldnames = ["url", "first_name", "last_name", "headline", "about", "match", "reason", "score"]
            else:
                fieldnames = ["url", "first_name", "last_name", "headline", "about"]
            
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
                'message': f'Successfully extracted {len(profile_data)} leads from URL'
            }
            
        except Exception as e:
            print(f"❌ Error during lead extraction from URL: {e}")
            return {
                'success': False,
                'error': f'Error during lead extraction from URL: {str(e)}'
            }

    def extract_leads(self, target_count=30, search_term='', country_filter='', include_country=True, position_filter='', include_position=True, extract_profile_data=True, use_ai_filtering=False, base_prompt=None):
        """
        Extract LinkedIn leads using pagination approach with optional profile data extraction, country filtering, and position filtering
        """
        if not self.driver:
            raise Exception("Browser not initialized. Please login first.")
        
        try:
            search_url = "https://www.linkedin.com/sales/search/people"
            print(f"🔍 Navigating to search URL...")
            self.driver.get(search_url)
            time.sleep(5)

            # If a search term is provided, enter it in the search bar and submit
            if search_term:
                try:
                    print(f"🔎 Entering search term: {search_term}")
                    search_input = self.driver.find_element(By.CLASS_NAME, "global-typeahead-search__input")
                    search_input.clear()
                    search_input.send_keys(search_term)
                    from selenium.webdriver.common.keys import Keys
                    search_input.send_keys(Keys.ENTER)
                    time.sleep(5)
                except Exception as e:
                    print(f"❌ Could not perform search: {e}")

            # Apply country filters if provided
            if country_filter:
                try:
                    print("🌍 Opening location filter panel...")
                    # Use the more reliable approach to find and click the GEOGRAPHY fieldset
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    # Wait for the GEOGRAPHY fieldset
                    fieldset = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//fieldset[@data-x-search-filter='GEOGRAPHY']"))
                    )
                    
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", fieldset)
                    
                    # Now try to click a likely clickable child
                    click_target = fieldset.find_element(By.XPATH, ".//div[contains(@class, 'ph4')]")
                    
                    # Use ActionChains to click reliably
                    actions = ActionChains(self.driver)
                    actions.move_to_element(click_target).click().perform()
                    
                    print("✅ Found and clicked location filter button")
                    time.sleep(2)  # Wait for filter panel to open
                    
                    # Now add all countries
                    for country in country_filter:
                        try:
                            print(f"🌍 Applying country filter: {country}")
                            country_input = self.driver.find_element(By.CLASS_NAME, "search-filter__focus-target--input")
                            country_input.clear()
                            time.sleep(0.5)
                            country_input.send_keys(country)
                            time.sleep(0.5)
                            if include_country:
                                self.driver.find_element(By.CLASS_NAME, "_include-button_1cz98z").click()
                            else:
                                self.driver.find_element(By.CLASS_NAME, "_exclude-button_1cz98z").click()
                            print(f"✅ Country filter applied: {country}")
                            time.sleep(1.5)  # Let UI update
                        except Exception as e:
                            print(f"❌ Could not apply country filter for {country}: {e}")
                except Exception as e:
                    print(f"❌ Could not open location filter panel: {e}")

            # Apply position filters if provided
            if position_filter:
                try:
                    print("👔 Opening position filter panel...")
                    # Use the more reliable approach to find and click the TITLE fieldset
                    # Wait for the TITLE fieldset
                    fieldset = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//fieldset[@data-x-search-filter='CURRENT_TITLE']"))
                    )
                    
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", fieldset)
                    
                    # Now try to click a likely clickable child
                    click_target = fieldset.find_element(By.XPATH, ".//div[contains(@class, 'ph4')]")
                    
                    # Use ActionChains to click reliably
                    actions = ActionChains(self.driver)
                    actions.move_to_element(click_target).click().perform()
                    
                    print("✅ Found and clicked position filter button")
                    time.sleep(2)  # Wait for filter panel to open
                    
                    # Now add all positions
                    for position in position_filter:
                        try:
                            print(f"👔 Applying position filter: {position}")
                            position_input = self.driver.find_element(By.CLASS_NAME, "search-filter__focus-target--input")
                            position_input.clear()
                            time.sleep(0.5)
                            position_input.send_keys(position)
                            time.sleep(0.5)
                            if include_position:
                                self.driver.find_element(By.CLASS_NAME, "_include-button_1cz98z").click()
                            else:
                                self.driver.find_element(By.CLASS_NAME, "_exclude-button_1cz98z").click()
                            print(f"✅ Position filter applied: {position}")
                            time.sleep(1.5)  # Let UI update
                        except Exception as e:
                            print(f"❌ Could not apply position filter for {position}: {e}")
                except Exception as e:
                    print(f"❌ Could not open position filter panel: {e}")

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
                    
                    # 2. Find the target div using XPath and scroll to it
                    try:
                        target_div = self.driver.find_element(By.XPATH, "/html/body/main/div[1]/div[2]/div[2]/div[2]/div[4]")
                        
                        # Scroll the element into view
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_div)
                        
                        print("✅ Scrolled to the target div.")
                        
                        # Wait for 7 seconds as requested
                        print("⏳ Waiting 7 seconds for page to fully load...")
                        time.sleep(7)
                        
                    except Exception as e:
                        print(f"❌ Failed to locate or scroll to the div: {e}")
                        # Continue anyway, maybe the div structure changed
                        time.sleep(5)

                    # 3. Extract hrefs using the specified approach
                    print("🔍 Extracting hrefs from current page...")
                    
                    # Find the scrollable container again (in case page structure changed)
                    try:
                        scroll_container = self.driver.find_element(By.CLASS_NAME, "_border-search-results_1igybl")
                    except:
                        print("⚠️ Could not find scroll container, trying alternative approach")
                        scroll_container = self.driver
                    
                    # Find all title elements inside that container
                    title_elements = scroll_container.find_elements(By.CLASS_NAME, "artdeco-entity-lockup__title")
                    
                    print(f"📋 Found {len(title_elements)} title elements")
                    
                    # Extract hrefs
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
                                print(f"✅ Added href: {href}")
                        except Exception as e:
                            print(f"⚠️ Error extracting href from title element: {e}")
                            continue

                    print(f"✅ Collected {len(all_hrefs)} total leads (added {page_hrefs} from this page)")

                    if len(all_hrefs) >= target_count:
                        print(f"🎯 Target count reached: {len(all_hrefs)} leads")
                        break

                    # 4. Check if Next button exists and is clickable
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
                        profile = self.analyze_profile_with_ai(profile, base_prompt)
                        print(f"�� AI analysis result: {profile}")
                    
                    profile_data.append(profile)
                    time.sleep(2)  # Small delay between profile extractions
            else:
                # Just create basic profile data with URLs
                print(f"📋 Creating basic profile data for {len(all_hrefs)} leads...")
                profile_data = [{"url": href, "first_name": "", "last_name": "", "headline": "", "about": "", "match": "NO", "reason": "", "score": 0.0} 
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
                fieldnames = ["url", "first_name", "last_name", "headline", "about", "match", "reason", "score"]
            else:
                fieldnames = ["url", "first_name", "last_name", "headline", "about"]
            
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
                        'first_name': '',
                        'last_name': '',
                        'headline': '',
                        'about': '',
                        'match': 'NO',
                        'reason': '',
                        'score': 0.0
                    })
                else:
                    # New format - check if AI columns exist
                    profile_data = {
                        'url': row.get('url', ''),
                        'first_name': row.get('first_name', ''),
                        'last_name': row.get('last_name', ''),
                        'headline': row.get('headline', ''),
                        'about': row.get('about', ''),
                    }
                    
                    # Only add AI columns if they exist in the CSV
                    if 'match' in row:
                        profile_data['match'] = row.get('match', 'NO')
                    if 'reason' in row:
                        profile_data['reason'] = row.get('reason', '')
                    if 'score' in row:
                        profile_data['score'] = float(row.get('score', 0.0)) if row.get('score') else 0.0
                    
                    data.append(profile_data)
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
    return data 