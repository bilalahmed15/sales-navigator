from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
import time
import os
from dotenv import load_dotenv
from linkedin_login import LinkedInLogin
from lead_extractor import LeadExtractor, read_csv_data

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
        
        return render_template('view_leads.html', 
                             data=data,
                             filename=filename,
                             count=len(data))
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
        
        extract_profile_data = request.form.get('extract_profile_data', 'true').lower() == 'true'
        use_ai_filtering = request.form.get('use_ai_filtering', 'false').lower() == 'true'
        openai_api_key = request.form.get('openai_api_key', '')
        
        # Create LeadExtractor instance
        extractor = LeadExtractor(linkedin.driver, openai_api_key if openai_api_key else None)
        
        # Extract leads with profile data and AI filtering
        result = extractor.extract_leads(
            target_count=target_count,
            extract_profile_data=extract_profile_data,
            use_ai_filtering=use_ai_filtering
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

        success, message = linkedin.login(email, password)
        
        if success:
            # Set session as logged in
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

@app.route('/logout', methods=['POST'])
def logout():
    try:
        linkedin.quit()
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 