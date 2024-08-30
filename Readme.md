## Telemedicine

1. Required Python version
2. Make virtual envirnment -- python -m venv venv
3. Activate virtualenv -- .\venv\Scripts\activate
4. Create .env file and add below parameters
    MONGODB_URI=mongodb://localhost:27017/
    MONGODB_DB=telemedicine
    SECRET_KEY=your_secret_key
5. Install Dependiencies -- pip install -r requirements.txt / pip3 install -r requirements.txt
6. Run the app -- python manage.py runserver