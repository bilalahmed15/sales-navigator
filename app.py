from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
import time
import os
from dotenv import load_dotenv
from linkedin_login import LinkedInLogin
from lead_extractor import LeadExtractor, read_csv_data
from selenium.webdriver.common.by import By
from openai import OpenAI
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

# Global LinkedIn login instance
linkedin = LinkedInLogin()

@app.route('/')
def index():
    if not session.get('logged_in'):
        return render_template('login.html')
    return render_template('home.html')

@app.route('/view-leads')
def view_leads():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    filename = session.get('last_export')
    if not filename:
        return render_template('home.html', error="No leads file available. Please extract leads first.")
    
    try:
        data = read_csv_data(filename)
        print(f"Debug: Loaded {len(data)} rows from {filename}")
        if data:
            print(f"Debug: First row keys: {list(data[0].keys())}")
            print(f"Debug: First row: {data[0]}")
        
        # Filter leads with score > 0.5
        filtered_data = [row for row in data if float(row.get('score', 0.0)) > 0.5]
        
        # Calculate stats
        total = len(filtered_data)
        match_yes = sum(1 for row in filtered_data if row.get('match', '').upper() == 'YES')
        success_rate = (match_yes / total * 100) if total > 0 else 0
        hot_leads_count = sum(1 for row in filtered_data if float(row.get('score', 0.0)) >= 0.7)
        
        return render_template('view_leads.html', 
                             data=filtered_data,
                             filename=filename,
                             count=total,
                             success_rate=success_rate,
                             hot_leads_count=hot_leads_count)
    except Exception as e:
        print(f"Error in view_leads: {e}")
        return render_template('home.html', error=str(e))

@app.route('/extract-leads', methods=['POST'])
def extract_leads():
    if 'logged_in' not in session:
        return jsonify({'error': 'Please log in first'}), 401
    
    if not linkedin.driver:
        return jsonify({'error': 'Browser not available. Please log in again.'}), 400
    
    try:
        # Get parameters from request
        target_count = request.form.get('target_count', 30, type=int)
        if target_count <= 0:
            target_count = 30
        
        search_term = request.form.get('search_term', '').strip()
        country_filter = request.form.getlist('country_filter[]')
        include_country = request.form.get('include_country', 'true').lower() == 'true'
        position_filter = request.form.getlist('position_filter[]')
        include_position = request.form.get('include_position', 'true').lower() == 'true'
        extract_profile_data = request.form.get('extract_profile_data', 'true').lower() == 'true'
        use_ai_filtering = request.form.get('use_ai_filtering', 'false').lower() == 'true'
        openai_api_key = request.form.get('openai_api_key', '')
        base_prompt = request.form.get('base_prompt', '').strip()
        
        # Create LeadExtractor instance
        extractor = LeadExtractor(linkedin.driver, openai_api_key if openai_api_key else None)
        
        # Extract leads with profile data and AI filtering
        result = extractor.extract_leads(
            target_count=target_count,
            search_term=search_term,
            country_filter=country_filter,
            include_country=include_country,
            position_filter=position_filter,
            include_position=include_position,
            extract_profile_data=extract_profile_data,
            use_ai_filtering=use_ai_filtering,
            base_prompt=base_prompt
        )
        
        if result['success']:
            # Save filename in session for later use
            session['last_export'] = result['filename']
            
            return jsonify({
                'message': result['message'],
                'count': result['count'],
                'filename': result['filename']
            })
        else:
            return jsonify({'error': result['error']}), 500
        
    except Exception as e:
        print(f"❌ Error during lead extraction: {e}")
        return jsonify({'error': f'Error during lead extraction: {str(e)}'}), 500

@app.route('/extract-from-link', methods=['POST'])
def extract_from_link():
    if 'logged_in' not in session:
        return jsonify({'error': 'Please log in first'}), 401
    
    if not linkedin.driver:
        return jsonify({'error': 'Browser not available. Please log in again.'}), 400
    
    try:
        # Get parameters from request
        linkedin_url = request.form.get('linkedin_url', '').strip()
        target_count = request.form.get('target_count', 30, type=int)
        
        print(f"🔍 Received LinkedIn URL: {linkedin_url}")
        print(f"🔍 Received target count: {target_count}")
        print(f"🔍 All form data: {dict(request.form)}")
        print(f"🔍 LinkedIn URL length: {len(linkedin_url) if linkedin_url else 0}")
        print(f"🔍 LinkedIn URL starts with: {linkedin_url[:50] if linkedin_url else 'None'}...")
        
        if not linkedin_url:
            print("❌ No LinkedIn URL provided")
            return jsonify({'error': 'LinkedIn URL is required'}), 400
        
        if target_count <= 0:
            target_count = 30
        
        openai_api_key = request.form.get('openaiApiKey', '').strip()
        base_prompt = request.form.get('basePrompt', '').strip()
        use_ai_filtering = bool(openai_api_key and base_prompt)

        extractor = LeadExtractor(linkedin.driver, openai_api_key if openai_api_key else None)

        result = extractor.extract_leads_from_url(
            linkedin_url=linkedin_url,
            target_count=target_count,
            use_ai_filtering=use_ai_filtering,
            base_prompt=base_prompt if use_ai_filtering else None
        )
        
        if result['success']:
            # Save filename in session for later use
            session['last_export'] = result['filename']
            
            return jsonify({
                'message': result['message'],
                'count': result['count'],
                'filename': result['filename']
            })
        else:
            return jsonify({'error': result['error']}), 500
        
    except Exception as e:
        print(f"❌ Error during lead extraction from link: {e}")
        return jsonify({'error': f'Error during lead extraction from link: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    try:
        return send_file(
            os.path.join("static", "exports", filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        status, message = linkedin.login(email, password)
        
        if status == '2fa':
            # 2FA required, prompt for code
            return jsonify({
                'success': False,
                '2fa_required': True,
                'message': message
            })
        elif status is True:
            session['logged_in'] = True
            return jsonify({
                'success': True,
                'message': message,
                'redirect': url_for('index')
            })
        else:
            return jsonify({'error': message}), 500
        
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

@app.route('/submit-2fa', methods=['POST'])
def submit_2fa():
    try:
        code = request.form.get('code')
        if not code:
            return jsonify({'error': 'Authentication code is required'}), 400
        status, message = linkedin.submit_2fa_code(code)
        if status:
            session['logged_in'] = True
            return jsonify({'success': True, 'message': message, 'redirect': url_for('index')})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    try:
        linkedin.quit()
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/message-leads')
def message_leads():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    filename = session.get('last_export')
    if not filename:
        return redirect(url_for('view_leads'))
    data = read_csv_data(filename)
    return render_template('message_leads.html', data=data, count=len(data))

@app.route('/start-messaging', methods=['POST'])
def start_messaging():
    if not session.get('logged_in'):
        return jsonify({'error': 'Not logged in'}), 401
    filename = session.get('last_export')
    if not filename:
        return jsonify({'error': 'No leads file found'}), 400
    data = read_csv_data(filename)
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    if not subject or not message:
        return jsonify({'error': 'Subject and message are required'}), 400
    try:
        for row in data:
            url = row.get('url')
            if not url:
                continue
            linkedin.driver.get(url)
            time.sleep(3)
            try:
                message_button = linkedin.driver.find_element(By.CLASS_NAME, "_message-cta_1xow7n")
                message_button.click()
                time.sleep(2)
                subject_field = linkedin.driver.find_element(By.CLASS_NAME, "_subject-field_jrrmou")
                subject_field.send_keys(subject)
                message_field = linkedin.driver.find_element(By.XPATH, "/html/body/div[8]/section/div[2]/section/form[1]/fieldset[1]/div/div8")
                message_field.send_keys(message)
                send_button = linkedin.driver.find_element(By.XPATH, "/html/body/div[8]/section/div[2]/section/form[1]/fieldset[2]/section/div/button[2]")
                send_button.click()
                time.sleep(2)
            except Exception as e:
                print(f"Failed to message {url}: {e}")
                continue
        return jsonify({'success': True, 'message': 'Messaging started/completed.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate-keywords', methods=['POST'])
def generate_keywords():
    try:
        base_prompt = request.form.get('base_prompt', '').strip()
        openai_api_key = request.form.get('openai_api_key', '').strip()
        
        if not base_prompt:
            return jsonify({'error': 'Base prompt is required'}), 400
        
        if not openai_api_key:
            return jsonify({'error': 'OpenAI API key is required'}), 400
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)
        
        # Create prompt for keyword generation
        prompt = f"""
        You are an expert B2B sales assistant specializing in LinkedIn Sales Navigator keyword generation.

        Based on the following client requirements, generate 8-12 targeted keywords that would be effective for finding relevant professionals on LinkedIn Sales Navigator.

        Client Requirements:
        {base_prompt}

        Generate keywords that:
        1. Are specific to the industry/role mentioned
        2. Include job titles, skills, and industry terms
        3. Are commonly used in LinkedIn profiles
        4. Will help find decision-makers and relevant professionals
        5. Are 1-3 words each (avoid long phrases)

        Return ONLY a JSON array of strings, like this:
        ["keyword1", "keyword2", "keyword3", ...]

        Example for tech industry:
        ["Software Engineer", "Product Manager", "Data Scientist", "Machine Learning", "Python", "React", "AWS", "DevOps", "Agile", "Scrum Master"]
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse the JSON response
        import json
        try:
            # Remove any markdown formatting if present
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            keywords = json.loads(content)
            
            if not isinstance(keywords, list):
                return jsonify({'error': 'Invalid response format from AI'}), 500
            
            return jsonify({
                'success': True,
                'keywords': keywords
            })
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw content: {content}")
            return jsonify({'error': 'Failed to parse AI response'}), 500
        
    except Exception as e:
        print(f"Error generating keywords: {e}")
        return jsonify({'error': f'Error generating keywords: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True) 