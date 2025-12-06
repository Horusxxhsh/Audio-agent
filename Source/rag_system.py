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
        
        print(f"RAG System initialized. Vector DB: {persist_directory}")
    
    def _get_or_create_collection(self, name: str):
        """获取或创建集合"""
        try:
            collection = self.chroma_client.get_collection(name)
            print(f"Collection '{name}' loaded with {collection.count()} documents")
        except:
            collection = self.chroma_client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Collection '{name}' created")
        return collection
    
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
                            user_rating: Optional[str] = None):
        """
        添加参数预设到向量数据库
        
        Args:
            preset_name: 预设名称
            parameters: 参数字典
            style_tags: 风格标签
            description: 描述
            user_rating: 用户评价（accept/edit/reject）
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
        
        # 添加到集合
        try:
            self.parameter_collection.add(
                documents=[doc_text],
                ids=[doc_id],
                metadatas=[doc_metadata]
            )
            print(f"Added parameter preset: {preset_name}")
        except Exception as e:
            # 如果已存在则更新
            try:
                self.parameter_collection.update(
                    ids=[doc_id],
                    documents=[doc_text],
                    metadatas=[doc_metadata]
                )
                print(f"Updated parameter preset: {preset_name}")
            except Exception as e2:
                print(f"Error adding parameter preset: {e2}")
    
    def retrieve_similar_knowledge(self, 
                                   query: str,
                                   n_results: int = 5,
                                   collection_type: str = "music") -> List[Dict[str, Any]]:
        """
        检索相似的知识
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            collection_type: 集合类型（"music" 或 "parameter"）
            
        Returns:
            相似文档列表
        """
        collection = self.music_collection if collection_type == "music" else self.parameter_collection
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # 格式化结果
            formatted_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    formatted_results.append({
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None
                    })
            
            return formatted_results
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []
    
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
                            n_recommendations: int = 3) -> List[Dict[str, Any]]:
        """
        基于 RAG 推荐参数
        
        Args:
            style_tags: 风格标签
            user_description: 用户描述
            n_recommendations: 推荐数量
            
        Returns:
            推荐的参数列表
        """
        # 构建查询
        query = f"{user_description} {' '.join(style_tags)}"
        
        # 检索相似参数预设
        similar_presets = self.retrieve_similar_knowledge(
            query,
            n_results=n_recommendations,
            collection_type="parameter"
        )
        
        # 解析并返回参数
        recommendations = []
        for preset in similar_presets:
            try:
                metadata = preset.get('metadata', {})
                parameters = json.loads(metadata.get('parameters', '{}'))
                recommendations.append({
                    'preset_name': metadata.get('preset_name', 'Unknown'),
                    'parameters': parameters,
                    'style_tags': json.loads(metadata.get('style_tags', '[]')),
                    'similarity': 1 - preset.get('distance', 1.0),
                    'user_rating': metadata.get('user_rating', 'neutral')
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
        api_key="sk-1b73586fde854a329ec187dc371f53ef",
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
