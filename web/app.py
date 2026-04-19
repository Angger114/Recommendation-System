# app.py - Versi Lengkap dengan Perbaikan DynamoDB
from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask_cors import CORS
import logging
from functools import wraps
import time
import boto3
import json

# Enhanced Flask setup
load_dotenv()
app = Flask(__name__)
CORS(app)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Configuration
app.config.update(
    PREDICTION_API_URL=os.getenv('PREDICTION_API_URL'),
    API_KEY=os.getenv('API_GATEWAY_KEY'),
    REQUEST_TIMEOUT=10,
    AWS_REGION=os.getenv('AWS_REGION', 'us-east-1'),
    DYNAMODB_TABLE=os.getenv('DYNAMODB_TABLE', 'ProductEmbeddings')
)

# Initialize AWS clients with error handling
try:
    boto3.setup_default_session(
        region_name=app.config['AWS_REGION'],
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN')
    )
    dynamodb = boto3.resource('dynamodb')
    
    # Verify table exists
    table = dynamodb.Table(app.config['DYNAMODB_TABLE'])
    table.load()
    logger.info(f"Successfully connected to DynamoDB table: {app.config['DYNAMODB_TABLE']}")
    
except Exception as e:
    logger.error(f"AWS initialization failed: {str(e)}")
    dynamodb = None
    table = None

# Enhanced logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Starting request: {request.method} {request.path}")
        
        try:
            response = f(*args, **kwargs)
            duration = round((time.time() - start_time) * 1000, 2)
            
            if isinstance(response, tuple):
                response_obj = response[0]
                status_code = response[1] if len(response) > 1 else 200
            else:
                response_obj = response
                status_code = response.status_code if hasattr(response, 'status_code') else 200
            
            if isinstance(response_obj, str):
                response_obj = app.make_response(response_obj)
                status_code = response_obj.status_code
            
            logger.info(
                f"Completed request: {request.method} {request.path} "
                f"Status: {status_code} "
                f"Duration: {duration}ms"
            )
            
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
            
    return decorated_function

# Routes
@app.route('/')
@log_request
def index():
    return render_template('index.html')

@app.route('/recommendation')
@log_request
def recommendation():
    return render_template('recommendation.html')


# API Endpoints
@app.route('/api/recommend', methods=['POST'])
@log_request
def recommend():
    try:
        # Validate input
        if not request.is_json:
            raise ValueError("Request must be JSON")
        
        data = request.get_json()
        if not data:
            raise ValueError("Empty request body")
        
        required_fields = ['user_id']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Build API Gateway URL - IMPORTANT FIX HERE
        base_url = app.config['PREDICTION_API_URL'].rstrip('/')
        api_url = f"{base_url}/recommend"  # Construct full endpoint URL
        
        # Prepare headers
        headers = {
            'x-api-key': app.config['API_KEY'],
            'Content-Type': 'application/json'
        }

        # Debug logging
        logger.info(f"User ID: {data.get('user_id')}")
        logger.info(f"Calling API endpoint: {api_url}")
        logger.debug(f"Request payload: {json.dumps(data, indent=2)}")

        # Make API request
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            timeout=app.config['REQUEST_TIMEOUT']
        )
        logger.info(f"API URL: {api_url}")
        logger.info(f"STATUS: {response.status_code}")
        logger.info(f"RESPONSE: {response.text}")

        # Handle response
        if response.status_code == 200:
            lambda_response = response.json()
            if 'body' in lambda_response:
                body = json.loads(lambda_response['body'])
            else:
                body = lambda_response
                
            if not body.get('recommendations'):
                body['recommendations'] = []

            return jsonify(body)
        else:
            error_msg = f"API returned {response.status_code}"
            logger.error(f"{error_msg}: {response.text}")
            return jsonify({
                "error": error_msg,
                "api_response": response.text,
                "status": "error"
            }), 502

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 400
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API connection error: {str(e)}")
        return jsonify({
            "error": "Recommendation service unavailable",
            "details": str(e),
            "status": "error"
        }), 503
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e),
            "status": "error"
        }), 500

def validate_prediction_input(request):
    """Enhanced input validation"""
    if not request.is_json:
        raise ValueError("Request must be JSON")
    
    data = request.get_json()
    
    if not data:
        raise ValueError("Empty request body")
    
    # Validate required fields
    required_fields = ['user_id']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    return {
        "user_id": str(data['user_id'])
    }

def make_api_request(url, payload, api_key, endpoint_name, max_retries=2):
    """Enhanced API request with retries"""
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }
    
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=app.config['REQUEST_TIMEOUT']
            )
            
            if response.status_code == 200:
                return response
                
            last_error = f"API returned {response.status_code}: {response.text}"
            
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            
        if attempt < max_retries:
            wait_time = (attempt + 1) * 0.5  # Exponential backoff
            logger.warning(f"Retry {attempt + 1} for {endpoint_name} after {wait_time}s")
            time.sleep(wait_time)
    
    raise Exception(f"{endpoint_name} API failed after {max_retries} retries: {last_error}")



if __name__ == '__main__':
    app.run(host=os.getenv('FLASK_HOST'), port=os.getenv('FLASK_PORT'), debug=os.getenv('FLASK_DEBUG'))
