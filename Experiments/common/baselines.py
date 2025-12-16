import json
import random
import math

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("Warning: scikit-learn not found. Retrievers will fallback to simpler methods.")
    TfidfVectorizer = None
    cosine_similarity = None

# --- Helper Logic: Vector Math ---
def cosine_similarity_manual(v1, v2):
    dot_product = sum(a*b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a*a for a in v1))
    magnitude2 = math.sqrt(sum(b*b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

# --- Retriever Classes ---

class TextRetriever:
    """
    Retrieves knowledge base items based on Text Similarity.
    Uses TF-IDF if available, else Jaccard.
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
        style = " ".join(item.get('Style', []))
        feature = " ".join(item.get('Feature', []))
        return f"{style} {feature}"

    def retrieve_top_k(self, query_text, k=3):
        if not self.vectorizer:
            # Fallback: Jaccard
            scores = []
            q_tokens = set(query_text.lower().split())
            for item in self.training_data:
                txt = self._get_text_repr(item).lower()
                i_tokens = set(txt.split())
                if not q_tokens or not i_tokens:
                    score = 0
                else:
                    score = len(q_tokens & i_tokens) / len(q_tokens | i_tokens)
                scores.append((score, item))
            scores.sort(key=lambda x: x[0], reverse=True)
            return [x[1] for x in scores[:k]]

        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = similarities.argsort()[-k:][::-1]
        return [self.training_data[i] for i in top_indices]


class DualModalRetriever:
    """
    Retrieves items based on weighted Text + Audio Similarity.
    """
    def __init__(self, training_data):
        self.text_retriever = TextRetriever(training_data)
        self.knowledge_base = []
        for item in training_data:
            vec_str = item.get('Vector', "")
            vec = []
            try:
                if isinstance(vec_str, str) and vec_str:
                    vec = [float(x) for x in vec_str.split(',')]
                elif isinstance(vec_str, list):
                    vec = vec_str
            except:
                pass
            
            self.knowledge_base.append({
                "item": item,
                "vector": vec,
                "text_idx": training_data.index(item) # Map back if needed
            })

    def retrieve_top_k(self, query_text, query_audio_vector=None, alpha=0.5, k=3):
        scores = []
        
        # Pre-calculate text scores (reuse text retriever internals if possible, or naive)
        # Here we use the text retriever's logic manually or naive jaccard for simplicity 
        # unless we expose scores from TextRetriever. 
        # For simplicity/robustness, we re-implement weighted scoring here.
        
        q_tokens = set(query_text.lower().split())

        for kb_item in self.knowledge_base:
            # 1. Text Score
            item_obj = kb_item["item"]
            txt = " ".join(item_obj.get('Style', []) + item_obj.get('Feature', [])).lower()
            t_tokens = set(txt.split())
            if not q_tokens or not t_tokens:
                text_score = 0.0
            else:
                text_score = len(q_tokens & t_tokens) / len(q_tokens | t_tokens)
            
            # 2. Audio Score
            audio_score = 0.0
            if query_audio_vector and kb_item["vector"]:
                v1 = query_audio_vector
                v2 = kb_item["vector"]
                min_len = min(len(v1), len(v2))
                if min_len > 0:
                    audio_score = cosine_similarity_manual(v1[:min_len], v2[:min_len])
            
            # Fuse
            effective_alpha = alpha if query_audio_vector else 0.0
            final_score = (1 - effective_alpha) * text_score + effective_alpha * audio_score
            scores.append((final_score, item_obj))
            
        scores.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scores[:k]]


# --- Generative Agent ---

class GenerativeAgent:
    """
    Unified Generative Agent using DeepSeek.
    Supports:
    1. Zero-shot (No context)
    2. Text RAG (Text context)
    3. Dual RAG (Text+Audio context + CoT prompt)
    """
    def __init__(self):
        if OpenAI:
            self.client = OpenAI(api_key="sk-1b73586fde854a329ec187dc371f53ef", base_url="https://api.deepseek.com")
        else:
            print("Warning: openai module not found.")
            self.client = None
            
        self.effectors = [
            {"name": "compression", "format": '{"CompressorOn":{"Threshold":<float>,"Ratio":<float>,"Attack":<float>,"Release":<float>,"Makeup":<float>,"Mix":<float>}}'},
            {"name": "distortion", "format": '{"DriverOn":{"Distortion":<float>,"Volume":<float>}}'},
            {"name": "overload", "format": '{"ScreamerOn":{"Drive":<float>,"Tone":<float>,"Level":<float>}}'},
            {"name": "delay", "format": '{"DelayOn":{"Feedback":<float>,"Delay":<float>,"Mix":<float>}}'},
            {"name": "reverb", "format": '{"ReverbOn":{"Size":<float>,"Damping":<float>,"Width":<float>,"Mix":<float>}}'},
            {"name": "chorus", "format": '{"ChorusOn":{"Delay":<float>,"Depth":<float>,"Frequency":<float>,"Width":<float>}}'},
            {"name": "flanger", "format": '{"FlangerOn":{"Delay":<float>,"Depth":<float>,"Feedback":<float>,"Frequency":<float>,"Width":<float>}}'},
            {"name": "equalization", "format": '{"EqualiserOn":{"100hz":<float>,"200hz":<float>,"400hz":<float>,"800hz":<float>,"1600hz":<float>,"3200hz":<float>,"6400hz":<float>,"Level":<float>}}'},
            {"name": "phase", "format": '{"PhaserOn":{"Depth":<float>,"Feedback":<float>,"Frequency":<float>,"Width":<int>}}'}
        ]

    def _analyze_style(self, user_input):
        if not self.client:
            return [user_input]
        try:
            resp = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": f"Extract music style tags for: '{user_input}'. Output JSON list keys 'tags'."}],
                stream=False
            )
            content = resp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
            s = content.find('{')
            e = content.rfind('}')
            if s!=-1 and e!=-1:
                return json.loads(content[s:e+1]).get("tags", [user_input])
            return [user_input]
        except:
            return [user_input]

    def generate(self, user_input, context_items=None, mode="zero_shot"):
        """
        mode: 
          - 'zero_shot': No context.
          - 'rag': Use context (Text RAG).
          - 'rag_cot': Use context + CoT (Dual RAG).
        """
        if not self.client:
            return {}

        song_style = self._analyze_style(user_input)
        
        # Build Context String
        reference_str = "No references."
        if context_items:
            lines = []
            for item in context_items:
                line = f"Song: {item.get('SongName')}\nStyle: {item.get('Style')}\nParams: {item.get('Parameters')}\n"
                lines.append(line)
            reference_str = "\n".join(lines)

        final_params = {}

        # Select Prompt Template based on Mode
        base_instruction = "You are an audio effects expert."
        if mode == "zero_shot":
            instruction = f"{base_instruction} Generate parameters purely based on your knowledge of the style."
        elif mode == "rag":
            instruction = f"{base_instruction} Use the provided Reference Examples to guide your parameter generation."
        elif mode == "rag_cot":
            instruction = f"{base_instruction} The User Request might be vague or unrelated (noise). PRIORITIZE the Reference Examples (retrieved by audio similarity) as the ground truth for the intended sound. Think step-by-step how to adapt the References, then generate optimal parameters."
        
        prompt_template = (
             "{instruction}\n"
             "Request: {user_input}\n"
             "Tags: {song_style}\n\n"
             "--- References ---\n"
             "{reference_str}\n"
             "------------------\n\n"
             "Task: Generate JSON for {effector_name}.\n"
             "Output Format: {output_format}\n"
             "Strict JSON only."
        )

        # Generate each effector
        for eff in self.effectors:
            prompt = prompt_template.format(
                instruction=instruction,
                user_input=user_input,
                song_style=song_style,
                reference_str=reference_str,
                effector_name=eff['name'],
                output_format=eff['format']
            )
            
            try:
                resp = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    stream=False
                )
                content = resp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                s = content.find('{')
                e = content.rfind('}')
                if s != -1 and e != -1:
                    content = content[s:e+1]
                
                param_json = json.loads(content)
                final_params.update(param_json)
            except:
                pass
        
        return final_params
