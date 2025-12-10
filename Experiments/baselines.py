import json
import random

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("Warning: scikit-learn not found. BaselineB will use random retrieval.")
    TfidfVectorizer = None
    cosine_similarity = None

class BaselineA:
    """
    Direct LLM (Zero-shot) - Simulated
    In a real scenario, this would call OpenAI API to generate parameters from text.
    Here we simulate it by returning a random 'valid' parameter set from the training data 
    (or just a dummy fixed set if we want to be strict, but random is better for 'generation' feel).
    """
    def __init__(self):
        pass

    def generate(self, prompt, training_data=None):
        # Stub: Return a random parameter set from training data if available, else dummy
        if training_data:
            random_record = random.choice(training_data)
            return random_record['Parameters']
        return {"Note": "Simulated Baseline A Output"}

class BaselineB:
    """
    Text-Only RAG
    Retrieves parameters based on text similarity.
    """
    def __init__(self, training_data):
        self.training_data = training_data
        self.corpus = [self._get_text_repr(item) for item in training_data]
        self.vectorizer = None
        self.tfidf_matrix = None
        
        if TfidfVectorizer:
            self.vectorizer = TfidfVectorizer(stop_words='english')
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)

    def _get_text_repr(self, item):
        # Combine Style and Feature for text representation
        style = " ".join(item.get('Style', []))
        feature = " ".join(item.get('Feature', []))
        return f"{style} {feature}"

    def retrieve(self, query_text):
        if not self.vectorizer:
             # Fallback
             return random.choice(self.training_data)['Parameters']

        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top-1 index
        best_idx = similarities.argmax()
        return self.training_data[best_idx]['Parameters']

if __name__ == "__main__":
    # Test stub
    dummy_data = [
        {"Style": ["Rock"], "Feature": ["Distortion", "Loud"], "Parameters": {"Gain": 10}},
        {"Style": ["Jazz"], "Feature": ["Clean", "Warm"], "Parameters": {"Gain": 2}},
    ]
    
    print("--- Testing Baseline A ---")
    ba = BaselineA()
    print(ba.generate("Make it rock", dummy_data))
    
    print("\n--- Testing Baseline B ---")
    bb = BaselineB(dummy_data)
    print(bb.retrieve("I want a clean jazz tone"))
