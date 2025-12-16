import sys
import os
import shutil
import tempfile
import json
from typing import List, Dict, Any

# Add Source directory to path to import rag_system
current_dir = os.path.dirname(os.path.abspath(__file__))
source_dir = os.path.join(current_dir, '..', '..', 'Source')
sys.path.append(source_dir)

try:
    from rag_system import AudioRAGSystem
except ImportError:
    print("Error: Could not import AudioRAGSystem from Source. Make sure requirements are installed.")
    AudioRAGSystem = None

class RAGRetriever:
    """
    Adapter class to use AudioRAGSystem in experiments.
    Creates a TEMPORARY ChromaDB instance to identify knowledge base from training data
    without polluting the main user database.
    """
    def __init__(self, training_data: List[Dict]):
        if not AudioRAGSystem:
            raise ImportError("AudioRAGSystem not available")

        # Create a temporary directory for the vector DB
        self.temp_dir = tempfile.mkdtemp(prefix="audio_agent_experiment_")
        print(f"[RAGRetriever] Initializing temporary RAG DB at: {self.temp_dir}")

        # Initialize RAG System with temp dir
        # Priority: DEEPSEEK_API_KEY -> OPENAI_API_KEY -> Hardcoded Default
        default_key = "sk-1b73586fde854a329ec187dc371f53ef" 
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", default_key)
        
        self.rag = AudioRAGSystem(
            api_key=api_key,
            persist_directory=self.temp_dir,
            base_url="https://api.deepseek.com" # Explicitly force DeepSeek URL if using DeepSeek Key
        )

        # Populate DB with training data
        self._populate_db(training_data)

    def _populate_db(self, data: List[Dict]):
        print(f"[RAGRetriever] Populating DB with {len(data)} items...")
        for item in data:
            # We treat each dataset item as a "Parameter Preset"
            song_name = item.get('SongName', 'Unknown')
            params = item.get('Parameters', {})
            style = item.get('Style', [])
            feature = item.get('Feature', [])
            
            # Combine features into a description string
            description = ", ".join(feature) if feature else f"Style: {', '.join(style)}"
            
            # Add to RAG
            # Add to RAG
            raw_vector = item.get('Vector')
            vector = []
            if raw_vector:
                if isinstance(raw_vector, str):
                    # Handle string "0.1, 0.2"
                    try:
                        vector = [float(x) for x in raw_vector.split(',')]
                    except:
                        pass
                elif isinstance(raw_vector, list):
                    # Handle list ["0.1", "0.2"] or [0.1, 0.2]
                    try:
                        vector = [float(x) for x in raw_vector]
                    except:
                         pass
            
            self.rag.add_parameter_preset(
                preset_name=song_name,
                parameters=params,
                style_tags=style,
                description=description,
                user_rating="accept", # Assume training data is "good"
                audio_vector=vector
            )
            
    def retrieve_top_k(self, query_text: str, query_audio_vector=None, alpha=0.5, k=3):
        """
        Interprets the query for RAG and returns top-k items in the expected format.
        Note: Currently RAG is text-centric. Alpha/AudioVector are kept for interface compatibility
        but might be ignored or used only if RAG supports hybrid later.
        """
        # We need to extract style tags potentialy, but for ablation usually we have raw text.
        # RAG retrieve_similar_knowledge expects a query string.
        
        # 1. Retrieve
        # 1. Retrieve
        # Note: We now support audio_query_vector and weighted fusion
        results = self.rag.retrieve_similar_knowledge(
            query=query_text,
            n_results=k,
            collection_type="parameter",
            audio_query_vector=query_audio_vector,
            weight_audio=alpha
        )
        
        # 2. Convert back to dataset format
        retrieved_items = []
        for res in results:
            metadata = res.get('metadata', {})
            
            # Reconstruct item dict
            item = {
                "SongName": metadata.get('preset_name'),
                "Parameters": json.loads(metadata.get('parameters', '{}')),
                "Style": json.loads(metadata.get('style_tags', '[]')),
                "Feature": [metadata.get('description', '')], # Simplified
                # Vector is not returned by RAG metadata usually, but we don't strictly need it for Context
                "Vector": None 
            }
            retrieved_items.append(item)
            
        return retrieved_items

    def cleanup(self):
        """Clean up temporary directory"""
        try:
            # Close client if possible? Chroma 0.4+ usually handles via GC but good to be safe if specific close exists
            pass 
        except:
            pass
            
        if os.path.exists(self.temp_dir):
            print(f"[RAGRetriever] Cleaning up temp dir: {self.temp_dir}")
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp dir: {e}")

    def __del__(self):
        self.cleanup()
