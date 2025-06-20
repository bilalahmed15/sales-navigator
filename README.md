# LinkedIn Automation Flask App

This Flask application automates the process of logging into LinkedIn and fetching search results for specific queries.

## Prerequisites

- Python 3.7 or higher
- Chrome browser installed
- ChromeDriver (will be automatically installed by webdriver-manager)

## Setup

1. Clone this repository
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the Flask application:
   ```bash
   python app.py
   ```
2. Open your web browser and navigate to `http://localhost:5000`
3. Enter your LinkedIn credentials in the form
4. Click "Login and Fetch Results" to start the automation process

## Features

- Secure login form
- Automated LinkedIn login
- Fetches search results for anti-corrosion professionals
- Error handling and user feedback
- Modern, responsive UI

## Security Notes

- This application is for demonstration purposes only
- In a production environment, you should:
  - Use environment variables for sensitive data
  - Implement proper session management
  - Add rate limiting
  - Use HTTPS
  - Implement proper error handling
  - Add logging
  - Consider using a more robust solution for browser automation

## Disclaimer

This tool is meant for educational purposes only. Make sure to comply with LinkedIn's terms of service and automation policies when using this application. 