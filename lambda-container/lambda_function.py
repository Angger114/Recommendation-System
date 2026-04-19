import json
import boto3
import os
import pickle
from datetime import datetime
import logging
import sys
import random
from typing import Dict, Any, Tuple, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# 1. DEFINE THE MODEL CLASS IN THE SAME FILE
class HybridRecommender:
    """Complete implementation of the model class"""
    def __init__(self):
        self.model_version = "1.0"
        
    @staticmethod
    def predict_purchase_probability(user_features, product_features):
        """Enhanced prediction logic with proper scoring"""
        base_score = 0.5
        
        # User features scoring
        if user_features.get('purchase_history', 0) > 10:
            base_score += 0.25
        elif user_features.get('purchase_history', 0) > 5:
            base_score += 0.15
            
        if user_features.get('avg_spending', 0) > 200:
            base_score += 0.1
            
        # Product features scoring
        if product_features.get('price', 100) < 50:
            base_score += 0.15
        elif product_features.get('price', 100) < 100:
            base_score += 0.1
            
        if product_features.get('quality', 3) >= 4.5:
            base_score += 0.2
            
        return min(max(base_score, 0), 1)

# 2. MODEL LOADING WITH PROPER ERROR HANDLING
MODEL = None

def load_model(bucket: str, key: str):
    global MODEL

    local_path = '/tmp/model.pkl'

    # Use model directly if already in memory
    if MODEL is not None:
            return MODEL
    
    try:
        # if model is not exists in /tmp -> download from S3
        if not os.path.exists(local_path):
            logger.info("Downloading from S3...")
            s3.download_file(bucket, key, local_path)
        else:
            logger.info("Model already exists in /tmp")

        # load to memory
        with open(local_path, 'rb') as f:
            MODEL = pickle.load(f)
            logger.info("Model loaded successfully")
            return MODEL
            
    except Exception as e:
        logger.error(f"Model load failed: {str(e)}")
        raise Exception("MODEL LOAD FAILED")

# 3. IMPLEMENT THE MISSING get_features FUNCTION
def get_features(user_id: str, product_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Retrieve user and product features from DynamoDB or other sources
    Returns tuple of (user_features, product_features)
    """
    try:
        # Get user features from DynamoDB
        user_features = get_user_features(user_id)
        
        # Get product features from DynamoDB
        product_features = get_product_features(product_id)
        
        return user_features, product_features
        
    except Exception as e:
        logger.warning(f"Error getting features: {str(e)}. Using fallback features")
        return get_fallback_features(user_id, product_id)

def get_user_features(user_id: str) -> Dict[str, Any]:
    """Get user features from DynamoDB"""
    try:
        # Assuming you have a users table
        users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'techmart-users'))
        
        response = users_table.get_item(Key={'user_id': user_id})
        
        if 'Item' in response:
            item = response['Item']
            return {
                'purchase_history': int(item.get('purchase_count', 0)),
                'avg_spending': float(item.get('avg_spending', 0)),
                'age': int(item.get('age', 25)),
                'gender': item.get('gender', 'unknown'),
                'location': item.get('location', 'unknown'),
                'last_purchase_days': int(item.get('last_purchase_days', 30))
            }
        else:
            logger.warning(f"User {user_id} not found in database")
            return get_default_user_features()
            
    except Exception as e:
        logger.error(f"Error getting user features: {str(e)}")
        return get_default_user_features()

def get_product_features(product_id: str) -> Dict[str, Any]:
    """Get product features from DynamoDB"""
    try:
        # Assuming you have a products table
        products_table = dynamodb.Table(os.environ.get('PRODUCTS_TABLE', 'ProductEmbeddings'))
        
        response = products_table.get_item(Key={'product_id': product_id})
        
        if 'Item' in response:
            item = response['Item']
            return {
                'price': float(item.get('price', 100)),
                'quality': float(item.get('rating', 3.0)),
                'category': item.get('category', 'unknown'),
                'brand': item.get('brand', 'unknown'),
                'popularity': float(item.get('popularity_score', 0.5)),
                'stock_level': int(item.get('stock', 0))
            }
        else:
            logger.warning(f"Product {product_id} not found in database")
            return get_default_product_features()
            
    except Exception as e:
        logger.error(f"Error getting product features: {str(e)}")
        return get_default_product_features()

def get_default_user_features() -> Dict[str, Any]:
    """Default user features when data is not available"""
    return {
        'purchase_history': 3,
        'avg_spending': 75.0,
        'age': 30,
        'gender': 'unknown',
        'location': 'unknown',
        'last_purchase_days': 30
    }

def get_default_product_features() -> Dict[str, Any]:
    """Default product features when data is not available"""
    return {
        'price': 100.0,
        'quality': 3.5,
        'category': 'electronics',
        'brand': 'unknown',
        'popularity': 0.5,
        'stock_level': 10
    }

def get_fallback_features(user_id: str, product_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Fallback features when database is unavailable"""
    logger.info("Using fallback features due to database unavailability")
    
    # Generate some reasonable fallback features
    user_features = {
        'purchase_history': random.randint(1, 15),
        'avg_spending': random.uniform(50, 300),
        'age': random.randint(18, 65),
        'gender': random.choice(['male', 'female', 'unknown']),
        'location': 'unknown',
        'last_purchase_days': random.randint(1, 90)
    }
    
    product_features = {
        'price': random.uniform(20, 500),
        'quality': random.uniform(2.0, 5.0),
        'category': random.choice(['electronics', 'clothing', 'books', 'home']),
        'brand': 'unknown',
        'popularity': random.uniform(0.1, 0.9),
        'stock_level': random.randint(0, 50)
    }
    
    return user_features, product_features

# 4. ENHANCED LAMBDA HANDLER
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # Parse input with validation
        body = event
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
            
        user_id = body.get('user_id', 'default')
        product_id = body.get('product_id', 'default')
        
        # Initialize model
        model = load_model(
            os.environ.get('MODEL_BUCKET', 'techmart-ml-handi'),
            os.environ.get('MODEL_KEY', 'models/hybrid_model.pkl')
        )
        
        # Get features (with fallback values)
        #user_features, product_features = get_features(user_id, product_id)
        
        # Make prediction
        try:
            recommendations = model.recommend(user_id, n_recommendations=5)
            source = 'ml_model'
        except Exception as e:
            logger.warning(f"Model prediction failed: {str(e)}")
            recommendations = []
            source = 'fallback'
        
        # Format response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'recommendations': recommendations,
                'model_source': source,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            })
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }