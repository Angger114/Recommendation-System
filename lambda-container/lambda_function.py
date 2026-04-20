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

# 1. MODEL LOADING WITH PROPER ERROR HANDLING
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

#2. IMPLEMENT THE MISSING get_features FUNCTION

def get_product_features(product_id: str) -> Dict[str, Any]:
    try:
        products_table = dynamodb.Table(os.environ.get('PRODUCTS_TABLE', 'ProductEmbeddings'))

        response = products_table.get_item(Key={'product_id': product_id})

        if 'Item' in response:
            item = response['Item']

            embedding_raw = item.get('embedding', '{}')
            product_name = item.get('product_name', product_id)

            if isinstance(embedding_raw, str):
                embedding = json.loads(embedding_raw)
            else:
                embedding = embedding_raw

            brand = embedding.get('brand', 'Unknown')
            category = embedding.get('category', 'Product')
            price_range = embedding.get('price_range', 'medium')
            popularity = embedding.get('popularity', 0)

            return {
                'name': product_name,
                'category': category,
                'brand': brand,
                'price_range': price_range,
                'popularity': popularity
            }

        return {}

    except Exception as e:
        logger.error(f"Error getting product features: {str(e)}")
        return {}

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

# 3. ENHANCED LAMBDA HANDLER
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
        
        # Initialize model
        model = load_model(
            os.environ.get('MODEL_BUCKET', 'techmart-ml-handi'),
            os.environ.get('MODEL_KEY', 'models/hybrid_model.pkl')
        )
        
        # Get features (with fallback values)
        #user_features, product_features = get_features(user_id, product_id)
        
        # get recommendation
        try:
            recommendations = model.recommend(user_id, n_recommendations=5)
            source = 'ml_model'

            enriched_recommendations = []

            for item in recommendations:
                pid = item.get('product_id')

                product_features = get_product_features(pid)

                enriched_item = {
                    **item,
                    'name': product_features.get('name', item.get('product_id')),
                    'category': product_features.get('category', '-'),
                    'brand': product_features.get('brand', '-'),
                    'price_range': product_features.get('price_range', '-'),
                    'popularity': product_features.get('popularity', 0)
                }

                enriched_recommendations.append(enriched_item)

            recommendations = enriched_recommendations
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