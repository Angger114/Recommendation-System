import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD


# Content-based filtering
class ContentBasedRecommender:
    def __init__(self):
        self.product_features = None
        self.tfidf_matrix = None
        self.similarity_matrix = None
        
    def fit(self, products_df):
        """Train content-based model"""
        
        # Create content features
        products_df['content'] = (
            products_df['category'] + ' ' + 
            products_df['name']+ ' ' + 
            products_df['brand'] 
        )
        
        # TF-IDF Vectorization
        tfidf = TfidfVectorizer(max_features=1000, stop_words='english')
        self.tfidf_matrix = tfidf.fit_transform(products_df['content'])
        
        # Calculate similarity matrix
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)
        self.product_features = products_df
        
    def recommend(self, product_id, n_recommendations=10):
        """Get recommendations for a product"""
        
        try:
            idx = self.product_features[
                self.product_features['product_id'] == product_id
            ].index[0]
            
            # Get similarity scores
            sim_scores = list(enumerate(self.similarity_matrix[idx]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
            
            # Get top similar products
            similar_products = []
            for i, score in sim_scores[1:n_recommendations+1]:
                similar_products.append({
                    'product_id': self.product_features.iloc[i]['product_id'],
                    'similarity_score': score
                })
                
            return similar_products
            
        except Exception as e:
            print(f"Error in content recommend: {e}")
            return []

# Testing

# Collaborative filtering
class CollaborativeRecommender:
    def __init__(self):
        self.user_item_matrix = None
        self.svd_model = None
        self.user_embeddings = None
        self.item_embeddings = None
        
    def fit(self, user_item_df):
        """Train collaborative filtering model"""
        
        # Create user-item matrix
        self.user_item_matrix = user_item_df.pivot_table(
            index='user_id', 
            columns='product_id', 
            values='purchase_count', 
            fill_value=0
        )
        
        # Apply SVD
        self.svd_model = TruncatedSVD(n_components=50, random_state=42)
        self.user_embeddings = self.svd_model.fit_transform(self.user_item_matrix)
        self.item_embeddings = self.svd_model.components_.T
        
    def recommend(self, user_id, n_recommendations=10):
        """Get recommendations for a user"""
        
        try:
            user_idx = self.user_item_matrix.index.get_loc(user_id)
            user_vector = self.user_embeddings[user_idx]
            
            # Calculate scores for all items
            scores = np.dot(user_vector, self.item_embeddings.T)
            
            # Get top recommendations
            top_items = np.argsort(scores)[::-1][:n_recommendations]
            
            recommendations = []
            for item_idx in top_items:
                product_id = self.user_item_matrix.columns[item_idx]
                score = scores[item_idx]
                
                recommendations.append({
                    'product_id': product_id,
                    'prediction_score': score
                })
                
            return recommendations
            
        except Exception as e:
            print(f"Error in collaborative recommend: {e}")
            return []

# Hybrid recommender
class HybridRecommender:
    def __init__(self):
        self.content_model = ContentBasedRecommender()
        self.collaborative_model = CollaborativeRecommender()
        
    def fit(self, user_item_df, products_df):
        """Train both models"""
        self.content_model.fit(products_df)
        self.collaborative_model.fit(user_item_df)
        
    def recommend(self, user_id, n_recommendations=10):
        """Get hybrid recommendations"""
        
        # Get collaborative recommendations
        collab_recs = self.collaborative_model.recommend(user_id, n_recommendations)
        
        # If no collaborative recommendations, use content-based
        if not collab_recs:
            # Get user's most recent purchase for content-based
            # This would require additional logic
            return []
        
        # Weight and combine recommendations
        final_recs = []
        for rec in collab_recs[:n_recommendations]:
            final_recs.append({
                'product_id': rec['product_id'],
                'score': rec['prediction_score'] * 0.7,  # Weight collaborative
                'type': 'collaborative'
            })
            
        return final_recs
