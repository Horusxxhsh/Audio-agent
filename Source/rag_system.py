"""
RAG (Retrieval-Augmented Generation) System for Audio Agent
增强检索生成系统 - 用于音乐风格和参数推荐
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import hashlib


class AudioRAGSystem:
    """音频 RAG 系统 - 结合向量检索和 LLM 生成"""
    
    def __init__(self, 
                 api_key: str,
                 base_url: str = "https://api.deepseek.com",
                 persist_directory: Optional[str] = None):
        """
        初始化 RAG 系统
        
        Args:
            api_key: OpenAI API key
            base_url: API 基础 URL
            persist_directory: 向量数据库持久化目录
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 设置持久化目录
        if persist_directory is None:
            persist_directory = os.environ.get('SUPERTONAL_DIR', 
                                               'C:\\Users\\Public\\Documents\\Supertonal DSP')
            persist_directory = os.path.join(persist_directory, 'vector_db')
        
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)
        
        # 初始化 ChromaDB 客户端
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 创建或获取集合
        self.music_collection = self._get_or_create_collection("music_knowledge")
        self.parameter_collection = self._get_or_create_collection("parameter_presets")
        self.memory_collection = self._get_or_create_collection("user_preference_memory")
        
        # Audio collection for storing raw audio vectors
        # Note: We use a simple collection where we provide embeddings directly
        try:
            self.audio_collection = self.chroma_client.get_or_create_collection(
                name="audio_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Collection 'audio_knowledge' ready")
        except Exception as e:
            print(f"Error initializing audio_knowledge: {e}")
            self.audio_collection = None
        
        print(f"RAG System initialized. Vector DB: {persist_directory}")
    
    def _get_or_create_collection(self, name: str):
        """获取或创建集合"""
        try:
            # Use a standard, high-quality local embedding model compatible with DeepSeek (local execution)
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            
            try:
                collection = self.chroma_client.get_collection(name=name, embedding_function=ef)
                print(f"Collection '{name}' loaded with {collection.count()} documents")
            except:
                collection = self.chroma_client.create_collection(
                    name=name,
                    embedding_function=ef,
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"Collection '{name}' created")
            return collection
        except Exception as e:
            print(f"Error initializing collection {name} with SentenceTransformer: {e}")
            # Fallback to default
            return self.chroma_client.get_or_create_collection(name=name)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        使用 OpenAI API 生成文本嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        try:
            # 使用 DeepSeek 的 embedding 接口（如果支持）
            # 如果不支持，降级使用简单的 TF-IDF 向量
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",  # 或其他支持的模型
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            # 降级方案：使用简单的文本特征向量
            print(f"Embedding API error: {e}, using fallback method")
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str, dim: int = 384) -> List[float]:
        """
        简单的文本嵌入方法（降级方案）
        使用字符级哈希和词频生成固定维度向量
        """
        # 创建固定维度的零向量
        vector = np.zeros(dim)
        
        # 分词
        words = text.lower().split()
        
        # 使用哈希函数将词映射到向量空间
        for i, word in enumerate(words):
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = hash_val % dim
            vector[idx] += 1.0 / (i + 1)  # 位置权重
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector.tolist()
    
    def add_music_knowledge(self, 
                           style: str,
                           description: str,
                           features: List[str],
                           examples: List[str] = None,
                           metadata: Dict[str, Any] = None):
        """
        添加音乐知识到向量数据库
        
        Args:
            style: 音乐风格（如 "post_rock", "metal" 等）
            description: 风格描述
            features: 特征列表
            examples: 示例歌曲
            metadata: 额外元数据
        """
        # 构建文档内容
        doc_text = f"Style: {style}\n"
        doc_text += f"Description: {description}\n"
        doc_text += f"Features: {', '.join(features)}\n"
        if examples:
            doc_text += f"Examples: {', '.join(examples)}\n"
        
        # 生成唯一 ID
        doc_id = f"style_{style}_{hashlib.md5(style.encode()).hexdigest()[:8]}"
        
        # 准备元数据
        doc_metadata = {
            "type": "style_knowledge",
            "style": style,
            "features": json.dumps(features, ensure_ascii=False),
            "examples": json.dumps(examples or [], ensure_ascii=False)
        }
        if metadata:
            doc_metadata.update(metadata)
        
        # 添加到集合
        try:
            self.music_collection.add(
                documents=[doc_text],
                ids=[doc_id],
                metadatas=[doc_metadata]
            )
            print(f"Added music knowledge: {style}")
        except Exception as e:
            # 如果已存在则更新
            try:
                self.music_collection.update(
                    ids=[doc_id],
                    documents=[doc_text],
                    metadatas=[doc_metadata]
                )
                print(f"Updated music knowledge: {style}")
            except Exception as e2:
                print(f"Error adding music knowledge: {e2}")
    
    def add_parameter_preset(self,
                            preset_name: str,
                            parameters: Dict[str, Any],
                            style_tags: List[str],
                            description: str,
                            user_rating: Optional[str] = None,
                            audio_vector: Optional[List[float]] = None):
        """
        添加参数预设到向量数据库
        
        Args:
            preset_name: 预设名称
            parameters: 参数字典
            style_tags: 风格标签
            description: 描述
            user_rating: 用户评价（accept/edit/reject）
            audio_vector: Optional audio feature vector (from dataset or inference)
        """
        # 构建文档内容
        doc_text = f"Preset: {preset_name}\n"
        doc_text += f"Style: {', '.join(style_tags)}\n"
        doc_text += f"Description: {description}\n"
        doc_text += f"Parameters: {json.dumps(parameters, ensure_ascii=False)}\n"
        
        # 生成唯一 ID
        doc_id = f"preset_{preset_name}_{hashlib.md5(preset_name.encode()).hexdigest()[:8]}"
        
        # 准备元数据
        doc_metadata = {
            "type": "parameter_preset",
            "preset_name": preset_name,
            "style_tags": json.dumps(style_tags, ensure_ascii=False),
            "parameters": json.dumps(parameters, ensure_ascii=False),
            "user_rating": user_rating or "neutral"
        }
        
        # 1. 存入 Parameter Collection (Text-based)
        try:
            self.parameter_collection.add(
                documents=[doc_text],
                ids=[doc_id],
                metadatas=[doc_metadata]
            )
            print(f"Added parameter preset (Text): {preset_name}")
        except Exception as e:
            try:
                self.parameter_collection.update(
                    ids=[doc_id],
                    documents=[doc_text],
                    metadatas=[doc_metadata]
                )
                print(f"Updated parameter preset (Text): {preset_name}")
            except Exception as e2:
                print(f"Error adding parameter preset (Text): {e2}")

        # 2. 存入 Audio Collection (Audio-based)
        # FIX: Only add to audio_collection if vector has meaningful content
        # Empty vectors (len=0) will cause ChromaDB to return unreliable results
        if audio_vector is not None and self.audio_collection is not None:
            try:
                # Check if vector has content
                if len(audio_vector) > 0:
                    # Use the SAME ID and Metadata so we can link them back
                    self.audio_collection.add(
                        ids=[doc_id],
                        embeddings=[audio_vector],
                        metadatas=[doc_metadata],
                        documents=[doc_text] # Keeping text as doc is fine, but we'll search by vector
                    )
                    print(f"Added parameter preset (Audio): {preset_name}")
                else:
                    # Skip audio indexing for empty vectors
                    # These samples will still be in parameter_collection (text-only)
                    # And can be retrieved by TRR which has its own index
                    pass
            except Exception as e:
                try:
                    if len(audio_vector) > 0:
                        self.audio_collection.update(
                            ids=[doc_id],
                            embeddings=[audio_vector],
                            metadatas=[doc_metadata],
                            documents=[doc_text]
                        )
                        print(f"Updated parameter preset (Audio): {preset_name}")
                except Exception as e2:
                    print(f"Error adding parameter preset (Audio): {e2}")

    def save_to_memory(self,
                       query: str,
                       parameters: Dict[str, Any],
                       audio_vector: List[float],
                       metadata: Optional[Dict[str, Any]] = None):
        """
        将用户偏好（微调后的参数）保存到记忆库中 (TAM)
        
        Args:
            query: 原始自然语言查询
            parameters: 用户微调后的最终 DSP 参数
            audio_vector: 输入音频的 TRR 向量
            metadata: 额外元数据
        """
        # 构建文档内容
        doc_text = f"User Preference Memory\n"
        doc_text += f"Query: {query}\n"
        doc_text += f"Parameters: {json.dumps(parameters, ensure_ascii=False)}\n"
        
        # 使用时间戳和查询哈希生成唯一 ID
        import time
        timestamp = int(time.time())
        doc_id = f"mem_{timestamp}_{hashlib.md5(query.encode()).hexdigest()[:6]}"
        
        # 准备元数据
        doc_metadata = {
            "type": "user_memory",
            "query": query,
            "parameters": json.dumps(parameters, ensure_ascii=False),
            "timestamp": timestamp
        }
        if metadata:
            doc_metadata.update(metadata)
            
        try:
            self.memory_collection.add(
                ids=[doc_id],
                embeddings=[audio_vector],
                metadatas=[doc_metadata],
                documents=[doc_text]
            )
            print(f"Saved preference to memory: {query} (ID: {doc_id})")
        except Exception as e:
            print(f"Error saving to memory: {e}")

    def retrieve_similar_knowledge(self, 
                                   query: str,
                                   n_results: int = 5,
                                   collection_type: str = "music",
                                   audio_query_vector: Optional[List[float]] = None,
                                   weight_audio: float = 0.5) -> List[Dict[str, Any]]:
        """
        检索相似的知识 (支持加权融合排序 Weighted Fusion Ranking)
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            collection_type: 集合类型（"music" 或 "parameter"）
            audio_query_vector: Optional audio embedding vector
            weight_audio: Audio score weight (0.0 to 1.0). Text weight is (1-weight_audio).
            
        Returns:
            相似文档列表
        """
        target_collection = self.music_collection if collection_type == "music" else self.parameter_collection
        
        # 1. Fetch Candidates
        text_results = []
        audio_results = []
        memory_results = []
        
        # Memory Query (High Priority)
        if audio_query_vector is not None and collection_type == "parameter":
            try:
                raw_mem_res = self.memory_collection.query(
                    query_embeddings=[audio_query_vector],
                    n_results=n_results
                )
                if raw_mem_res['documents']:
                    for i in range(len(raw_mem_res['documents'][0])):
                        dist = raw_mem_res['distances'][0][i] if raw_mem_res['distances'] else 1.0
                        sim = max(0.0, 1.0 - dist)
                        # Memory Threshold check (e.g., 0.95 similarity)
                        if sim >= 0.90: # Slightly lower than 0.95 for flexibility in simulation
                            item = {
                                'document': raw_mem_res['documents'][0][i],
                                'metadata': raw_mem_res['metadatas'][0][i],
                                'id': raw_mem_res['ids'][0][i],
                                'score': sim,
                                'is_memory': True
                            }
                            memory_results.append(item)
            except Exception as e:
                print(f"Memory retrieval error: {e}")

        # Text Query
        try:
            if query and len(query.strip()) > 0:
                raw_text_res = target_collection.query(
                    query_texts=[query],
                    n_results=n_results * 2 # Fetch more for re-ranking
                )
                if raw_text_res['documents']:
                    for i in range(len(raw_text_res['documents'][0])):
                        dist = raw_text_res['distances'][0][i] if raw_text_res['distances'] else 1.0
                        # Convert Cosine Distance to Similarity (approx)
                        # Chroma Cosine Distance is 0..2 (1 - cos). Sim = 1 - Dist.
                        # Note: Sometimes Chroma returns Squared L2 if not configured. Assuming Cosine here as set in init.
                        sim = max(0.0, 1.0 - dist)
                        
                        item = {
                            'document': raw_text_res['documents'][0][i],
                            'metadata': raw_text_res['metadatas'][0][i],
                            'id': raw_text_res['ids'][0][i],
                            'score': sim
                        }
                        text_results.append(item)
        except Exception as e:
            print(f"Text retrieval error: {e}")

        # Audio Query
        if audio_query_vector is not None and collection_type == "parameter" and self.audio_collection is not None:
            try:
                raw_audio_res = self.audio_collection.query(
                    query_embeddings=[audio_query_vector],
                    n_results=n_results * 2
                )
                if raw_audio_res['documents']:
                    for i in range(len(raw_audio_res['documents'][0])):
                        dist = raw_audio_res['distances'][0][i] if raw_audio_res['distances'] else 1.0
                        sim = max(0.0, 1.0 - dist)
                        item = {
                            'document': raw_audio_res['documents'][0][i], # Might be same text
                            'metadata': raw_audio_res['metadatas'][0][i],
                            'id': raw_audio_res['ids'][0][i],
                            'score': sim
                        }
                        audio_results.append(item)
            except Exception as e:
                print(f"Audio retrieval error: {e}")
                
        # 2. Fusion (Rank Aggregation)
        # Create a map of all unique IDs
        unique_items = {}
        
        # Process Memory Results (Highest Priority)
        for item in memory_results:
            uid = item['id']
            unique_items[uid] = {
                'item': item,
                'audio_score': item['score'],
                'text_score': 1.0, # Treat as perfect text match for priority
                'is_memory': True
            }

        # Process Audio Results
        for item in audio_results:
            uid = item['id']
            if uid not in unique_items:
                unique_items[uid] = {
                    'item': item,
                    'audio_score': item['score'],
                    'text_score': 0.0 # Default if not found in text results
                }
            else:
                # Update audio score if higher
                unique_items[uid]['audio_score'] = max(unique_items[uid]['audio_score'], item['score'])
            
        # Process Text Results (Update or Add)
        for item in text_results:
            uid = item['id']
            if uid in unique_items:
                # Update text score if higher
                unique_items[uid]['text_score'] = max(unique_items[uid]['text_score'], item['score'])
            else:
                unique_items[uid] = {
                    'item': item,
                    'audio_score': 0.0,
                    'text_score': item['score']
                }
                
        # Calculate Final Weighted Score
        final_candidates = []
        for uid, data in unique_items.items():
            # Weighted Sum
            is_mem = data.get('is_memory', False)
            
            if is_mem:
                # Boost memory items significantly
                final_score = 1.0 + data['audio_score'] 
            else:
                final_score = (data['audio_score'] * weight_audio) + (data['text_score'] * (1.0 - weight_audio))
            
            candidate = data['item'].copy()
            candidate['distance'] = 1.0 - min(1.0, final_score) # Keep distance in 0..1 range
            candidate['fusion_score'] = final_score
            candidate['source_modality'] = 'memory' if is_mem else 'hybrid'
            final_candidates.append(candidate)
            
        # 3. Sort and Return Top K
        final_candidates.sort(key=lambda x: x['fusion_score'], reverse=True)
        
        # DEBUG
        print(f"DEBUG: Fusion - MemRes: {len(memory_results)}, AudioRes: {len(audio_results)}, TextRes: {len(text_results)}")
        if final_candidates:
             top = final_candidates[0]
             print(f"DEBUG: Top Candidate: Score={top['fusion_score']:.4f} (Audio={top.get('audio_score',-1):.2f}, Text={top.get('text_score',-1):.2f}), Modality={top.get('source_modality')}")
             
        return final_candidates[:n_results]
    
    def generate_with_rag(self,
                         user_query: str,
                         style_tags: List[str],
                         context_type: str = "both",
                         n_context: int = 3) -> str:
        """
        使用 RAG 生成回答
        
        Args:
            user_query: 用户查询
            style_tags: 风格标签
            context_type: 上下文类型（"music", "parameter", "both"）
            n_context: 检索上下文数量
            
        Returns:
            生成的回答
        """
        # 构建查询文本
        query_text = f"{user_query} {' '.join(style_tags)}"
        
        # 检索相关上下文
        contexts = []
        
        if context_type in ["music", "both"]:
            music_contexts = self.retrieve_similar_knowledge(
                query_text, 
                n_results=n_context,
                collection_type="music"
            )
            contexts.extend(music_contexts)
        
        if context_type in ["parameter", "both"]:
            param_contexts = self.retrieve_similar_knowledge(
                query_text,
                n_results=n_context,
                collection_type="parameter"
            )
            contexts.extend(param_contexts)
        
        # 构建增强的提示词
        context_str = "\n\n".join([
            f"[Context {i+1}]\n{ctx['document']}\nRelevance: {1 - ctx['distance']:.2f}" 
            for i, ctx in enumerate(contexts) if ctx.get('distance') is not None
        ])
        
        enhanced_prompt = f"""Based on the following knowledge base context, answer the user's question.

Retrieved Context:
{context_str}

User Query: {user_query}
Style Tags: {', '.join(style_tags)}

Please provide a detailed and accurate answer based on the context above."""

        # 调用 LLM 生成回答
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a professional music production assistant with deep knowledge of audio effects and music styles."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Generation error: {e}")
            return f"Error generating response: {e}"
    
    def recommend_parameters(self,
                            style_tags: List[str],
                            user_description: str,
                            n_recommendations: int = 3,
                            audio_query_vector: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        基于 RAG 推荐参数 (支持文本和音频混合检索)
        
        Args:
            style_tags: 风格标签
            user_description: 用户描述
            n_recommendations: 推荐数量
            audio_query_vector: Optional audio feature vector
            
        Returns:
            推荐的参数列表
        """
        all_results = []
        
        # 1. Audio Retrieval (High Priority)
        if audio_query_vector is not None:
            audio_results = self.retrieve_similar_knowledge(
                query="", # Ignored when vector provided
                n_results=n_recommendations,
                collection_type="parameter",
                audio_query_vector=audio_query_vector
            )
            all_results.extend(audio_results)
            
        # 2. Text Retrieval
        # 构建文本查询
        query = f"{user_description} {' '.join(style_tags)}"
        text_results = self.retrieve_similar_knowledge(
            query,
            n_results=n_recommendations,
            collection_type="parameter"
        )
        all_results.extend(text_results)
        
        # 3. Merge and Deduplicate
        unique_presets = {}
        for res in all_results:
            try:
                metadata = res.get('metadata', {})
                preset_name = metadata.get('preset_name', 'Unknown')
                
                # If already exists, keep the one with lower distance (better match)
                # Note: distances might not be directly comparable between modalities, 
                # but generally lower is better. We might prioritize audio source.
                current_distance = res.get('distance', 1.0)
                
                if preset_name not in unique_presets:
                    unique_presets[preset_name] = res
                else:
                    existing = unique_presets[preset_name]
                    if current_distance < existing.get('distance', 1.0):
                         unique_presets[preset_name] = res
            except:
                continue
        
        # Convert back to list and sort by distance
        final_results = list(unique_presets.values())
        final_results.sort(key=lambda x: x.get('distance', 1.0))
        final_results = final_results[:n_recommendations]
        
        # 解析并返回参数
        recommendations = []
        for preset in final_results:
            try:
                metadata = preset.get('metadata', {})
                parameters = json.loads(metadata.get('parameters', '{}'))
                recommendations.append({
                    'preset_name': metadata.get('preset_name', 'Unknown'),
                    'parameters': parameters,
                    'style_tags': json.loads(metadata.get('style_tags', '[]')),
                    'similarity': 1 - preset.get('distance', 1.0),
                    'user_rating': metadata.get('user_rating', 'neutral'),
                    'source_modality': preset.get('source_modality', 'unknown')
                })
            except Exception as e:
                print(f"Error parsing preset: {e}")
                continue
        
        return recommendations
    
    def get_collection_stats(self) -> Dict[str, int]:
        """获取集合统计信息"""
        return {
            "music_knowledge_count": self.music_collection.count(),
            "parameter_presets_count": self.parameter_collection.count()
        }
    
    def clear_collection(self, collection_type: str):
        """清空指定集合"""
        if collection_type == "music":
            self.chroma_client.delete_collection("music_knowledge")
            self.music_collection = self._get_or_create_collection("music_knowledge")
        elif collection_type == "parameter":
            self.chroma_client.delete_collection("parameter_presets")
            self.parameter_collection = self._get_or_create_collection("parameter_presets")
        print(f"Collection '{collection_type}' cleared")


def initialize_knowledge_base(rag_system: AudioRAGSystem):
    """
    初始化知识库 - 添加基础音乐风格知识
    """
    
    # 添加常见音乐风格知识
    music_styles = [
        {
            "style": "post_rock",
            "description": "Post-rock emphasizes atmosphere, texture, and dynamics over traditional rock structures. Often instrumental with gradual builds and ambient elements.",
            "features": ["reverb", "delay", "ambient_swells", "clean_to_distorted", "atmospheric", "emotional"],
            "examples": ["Explosions in the Sky", "Godspeed You! Black Emperor", "Mogwai"]
        },
        {
            "style": "metal",
            "description": "Heavy metal features aggressive distortion, palm-muted riffs, and powerful dynamics. Requires tight compression and high-gain tones.",
            "features": ["distortion", "compression", "palm_mute", "high_gain", "tight", "aggressive"],
            "examples": ["Metallica", "Slayer", "Iron Maiden"]
        },
        {
            "style": "djent",
            "description": "Djent is characterized by highly syncopated, palm-muted guitar riffs with precise articulation and polyrhythmic patterns.",
            "features": ["distortion", "compression", "palm_mute", "polyrhythmic", "syncopated", "tight"],
            "examples": ["Meshuggah", "Periphery", "TesseracT"]
        },
        {
            "style": "blues",
            "description": "Blues rock features expressive bends, vibrato, and pentatonic scales. Medium gain with natural tube compression.",
            "features": ["overload", "compression", "reverb", "expressive", "bends", "pentatonic"],
            "examples": ["B.B. King", "Stevie Ray Vaughan", "Eric Clapton"]
        },
        {
            "style": "ambient",
            "description": "Ambient music creates atmospheric soundscapes with heavy use of reverb, delay, and modulation effects.",
            "features": ["reverb", "delay", "chorus", "phaser", "atmospheric", "spacey", "ethereal"],
            "examples": ["Brian Eno", "Stars of the Lid", "Tim Hecker"]
        },
        {
            "style": "shoegaze",
            "description": "Shoegaze features walls of sound with heavy reverb, delay, and distortion creating dreamy, washed-out textures.",
            "features": ["reverb", "delay", "distortion", "chorus", "dreamy", "wall_of_sound", "fuzzy"],
            "examples": ["My Bloody Valentine", "Slowdive", "Ride"]
        }
    ]
    
    for style_data in music_styles:
        rag_system.add_music_knowledge(**style_data)
    
    print(f"Initialized knowledge base with {len(music_styles)} music styles")


if __name__ == "__main__":
    # 测试 RAG 系统
    print("=== Testing Audio RAG System ===")
    
    # 初始化
    rag = AudioRAGSystem(
        api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
        base_url="https://api.deepseek.com"
    )
    
    # 初始化知识库
    initialize_knowledge_base(rag)
    
    # 测试检索
    print("\n=== Testing Retrieval ===")
    results = rag.retrieve_similar_knowledge("atmospheric guitar with reverb and delay", n_results=3)
    for i, result in enumerate(results):
        print(f"\n[Result {i+1}]")
        print(result['document'][:200])
        print(f"Distance: {result.get('distance', 'N/A')}")
    
    # 测试生成
    print("\n=== Testing RAG Generation ===")
    response = rag.generate_with_rag(
        user_query="I want a atmospheric post-rock guitar sound",
        style_tags=["post_rock", "ambient", "atmospheric"]
    )
    print(response)
    
    # 显示统计
    print("\n=== Collection Statistics ===")
    stats = rag.get_collection_stats()
    print(stats)
