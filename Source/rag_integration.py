"""
集成 RAG 系统到现有的 llm.py
Enhanced version with RAG integration - V2
正确集成点：在LLM生成标签和描述之后进行检索
"""

import sys
import os
import json
from typing import List, Dict, Any, Optional

# 添加 RAG 系统导入
try:
    from rag_system import AudioRAGSystem, initialize_knowledge_base
    RAG_AVAILABLE = True
except ImportError:
    print("Warning: RAG system not available. Running in legacy mode.")
    RAG_AVAILABLE = False

# 在原有代码基础上，添加 RAG 增强功能


def integrate_rag_with_existing_system(
    chat_message: str,
    song_style: list,
    guitar_features: list,
    memoryEnabled: str,
    api_key: str = ""
):
    """
    将 RAG 系统集成到现有的推理流程中
    
    *** 重要修改 ***
    此函数应该在 LLM 生成 tags 和 description 之后调用
    而不是直接使用用户的原始输入 chat_message
    
    工作流程：
    1. 用户输入 chat_message → LLM分析 → 生成 song_style (tags) 和 guitar_features (description)
    2. 使用生成的 tags 和 description 进行 RAG 检索 ← 这里！
    3. RAG 检索结果用于增强参数生成提示词
    
    Args:
        chat_message: 用户原始输入（仅用于记录）
        song_style: LLM生成的风格标签（如 ["post_rock", "atmospheric"]）
        guitar_features: LLM生成的描述特征（如 ["reverb-drenched", "clean arpeggios"]）
        memoryEnabled: 是否启用记忆系统
        api_key: API 密钥
        
    Returns:
        增强后的上下文和推荐
    """
    if not RAG_AVAILABLE:
        return None
    
    try:
        # 初始化 RAG 系统
        rag = AudioRAGSystem(api_key=api_key, base_url="https://api.deepseek.com")
        
        # 确保知识库已初始化
        stats = rag.get_collection_stats()
        if stats['music_knowledge_count'] == 0:
            print("[RAG] Initializing knowledge base...")
            initialize_knowledge_base(rag)
        
        # *** 核心修改 ***
        # 使用LLM生成的标签和描述构建检索查询，而不是原始用户输入
        search_query = construct_search_query_from_generated_tags(
            tags=song_style,
            descriptions=guitar_features
        )
        
        print(f"[RAG] Original query: {chat_message}")
        print(f"[RAG] Generated tags: {song_style}")
        print(f"[RAG] Search query constructed from tags: {search_query}")
        
        # 1. 检索相关音乐知识（使用生成的标签）
        music_context = rag.retrieve_similar_knowledge(
            query=search_query,
            n_results=3,
            collection_type="music"
        )
        
        print(f"[RAG] Retrieved {len(music_context)} music knowledge entries")
        
        # 2. 检索相似参数预设（使用生成的标签和描述）
        description_str = extract_clean_descriptions(guitar_features)
        parameter_recommendations = rag.recommend_parameters(
            style_tags=song_style,
            user_description=description_str,
            n_recommendations=5  # 增加推荐数量
        )
        
        print(f"[RAG] Retrieved {len(parameter_recommendations)} parameter recommendations")
        
        # 3. 构建RAG增强提示词片段
        rag_enhanced_prompt = build_rag_context_for_parameters(
            music_context=music_context,
            parameter_recommendations=parameter_recommendations,
            generated_tags=song_style
        )
        
        return {
            "music_context": music_context,
            "parameter_recommendations": parameter_recommendations,
            "rag_enhanced_prompt": rag_enhanced_prompt,
            "search_query": search_query,
            "rag_stats": stats
        }
        
    except Exception as e:
        print(f"[RAG] Integration error: {e}")
        import traceback
        traceback.print_exc()
        return None


def construct_search_query_from_generated_tags(
    tags: List[str],
    descriptions: List[str]
) -> str:
    """
    根据LLM生成的标签和描述构建检索查询
    
    Args:
        tags: LLM生成的风格标签
        descriptions: LLM生成的描述特征
        
    Returns:
        优化的检索查询字符串
    """
    # 组合标签（标签更重要，重复2次增加权重）
    tags_str = ' '.join(tags) if tags else ''
    
    # 处理描述
    descriptions_str = extract_clean_descriptions(descriptions)
    
    # 构建查询：标签权重更高
    query = f"{tags_str} {tags_str} {descriptions_str}"
    
    return query.strip()


def extract_clean_descriptions(descriptions: List[str]) -> str:
    """
    提取并清理描述文本，移除结构化标记
    
    Args:
        descriptions: 描述列表
        
    Returns:
        清理后的描述字符串
    """
    if isinstance(descriptions, list):
        clean_descriptions = []
        for desc in descriptions:
            if isinstance(desc, str):
                # 移除分号后的结构化部分（如 "; guitar_solo: blues_rock_pentatonic"）
                if ';' in desc:
                    desc = desc.split(';')[0]
                clean_descriptions.append(desc)
        return ' '.join(clean_descriptions)
    else:
        return str(descriptions)


def build_rag_context_for_parameters(
    music_context: List[Dict],
    parameter_recommendations: List[Dict],
    generated_tags: List[str]
) -> str:
    """
    构建RAG上下文片段，用于注入到参数生成提示词中
    
    Args:
        music_context: 检索到的音乐知识
        parameter_recommendations: 推荐的参数预设
        generated_tags: LLM生成的风格标签
        
    Returns:
        格式化的RAG上下文字符串
    """
    context_parts = []
    
    # 1. 音乐风格知识摘要
    if music_context:
        context_parts.append("\n=== RAG Retrieved Style Knowledge ===")
        for i, ctx in enumerate(music_context[:2], 1):
            similarity = 1 - ctx.get('distance', 1.0)
            if similarity > 0.3:  # 只包含相关性高的
                metadata = ctx.get('metadata', {})
                style = metadata.get('style', 'Unknown')
                features = metadata.get('features', '[]')
                try:
                    features_list = json.loads(features)
                    features_str = ', '.join(features_list[:5])
                except:
                    features_str = str(features)[:100]
                
                context_parts.append(f"[Style {i}] {style} (similarity: {similarity:.2f})")
                context_parts.append(f"  Key features: {features_str}")
    
    # 2. 参数预设参考（按用户评分和相似度排序）
    if parameter_recommendations:
        context_parts.append("\n=== RAG Parameter Reference ===")
        
        # 排序：accept > edit > neutral/reject，相似度从高到低
        sorted_recs = sorted(
            parameter_recommendations,
            key=lambda x: (
                1 if x.get('user_rating') == 'accept' else 
                0.5 if x.get('user_rating') == 'edit' else 0,
                x.get('similarity', 0)
            ),
            reverse=True
        )
        
        for i, rec in enumerate(sorted_recs[:3], 1):
            similarity = rec.get('similarity', 0)
            if similarity > 0.3:
                preset_name = rec.get('preset_name', 'Unknown')
                rating = rec.get('user_rating', 'neutral')
                parameters = rec.get('parameters', {})
                
                context_parts.append(f"[Preset {i}] {preset_name}")
                context_parts.append(f"  Similarity: {similarity:.2f}, User rating: {rating}")
                
                # 显示启用的效果器
                enabled_effects = [key for key in parameters.keys() if key.endswith('On')]
                if enabled_effects:
                    context_parts.append(f"  Enabled effects: {', '.join(enabled_effects[:5])}")
                
                # 对于accept评分的预设，显示参数示例
                if rating == 'accept' and i == 1 and enabled_effects:
                    for effect_name in enabled_effects[:2]:
                        effect_params = parameters.get(effect_name, {})
                        if effect_params:
                            params_str = ', '.join([f"{k}={v}" for k, v in list(effect_params.items())[:3]])
                            context_parts.append(f"    {effect_name}: {params_str}")
    
    # 3. RAG使用指南
    if context_parts:
        context_parts.append("\n[RAG Guidance]")
        context_parts.append("- Use above knowledge as reference baseline")
        context_parts.append("- Prioritize 'accept' rated presets for parameter values")
        context_parts.append("- Adapt to style tags: " + ', '.join(generated_tags[:3]))
        context_parts.append("=== End of RAG Context ===\n")
    
    return '\n'.join(context_parts) if context_parts else ""


def add_preset_to_rag(
    rag_system: AudioRAGSystem,
    preset_name: str,
    parameters: dict,
    style_tags: list,
    features: list,
    user_rating: str = "neutral"
):
    """
    将新的参数预设添加到 RAG 知识库
    
    Args:
        rag_system: RAG 系统实例
        preset_name: 预设名称
        parameters: 参数字典
        style_tags: 风格标签（LLM生成的）
        features: 特征列表（LLM生成的描述）
        user_rating: 用户评价（accept/edit/reject）
    """
    try:
        description = extract_clean_descriptions(features)
        rag_system.add_parameter_preset(
            preset_name=preset_name,
            parameters=parameters,
            style_tags=style_tags,
            description=description,
            user_rating=user_rating
        )
        print(f"[RAG] Added preset '{preset_name}' with rating '{user_rating}' to knowledge base")
    except Exception as e:
        print(f"[RAG] Error adding preset: {e}")


def enhance_system_prompt_with_rag(
    original_prompt: str,
    rag_context: dict
) -> str:
    """
    使用 RAG 检索的上下文增强系统提示词
    
    修改：直接使用预构建的 rag_enhanced_prompt
    
    Args:
        original_prompt: 原始系统提示词
        rag_context: RAG 检索的上下文（包含 rag_enhanced_prompt 字段）
        
    Returns:
        增强后的提示词
    """
    if not rag_context:
        return original_prompt
    
    # 使用预构建的RAG提示词片段
    if rag_context.get('rag_enhanced_prompt'):
        return original_prompt + "\n\n" + rag_context['rag_enhanced_prompt']
    
    return original_prompt


# 示例：如何在现有代码中使用
def example_integration():
    """
    演示如何集成 RAG 到现有的 llm.py 流程
    展示正确的工作流程：LLM生成标签 → RAG检索 → 参数生成
    """
    print("=== 模拟 llm.py 实际工作流程 ===\n")
    
    # 步骤1：用户原始输入
    chat_message = "atmospheric post-rock guitar"
    print(f"步骤1 - 用户输入: {chat_message}")
    
    # 步骤2：LLM生成标签和描述（模拟 response2 的结果）
    # 在实际代码中，这是通过 client.chat.completions.create() 获得的
    result2 = {
        "tags": ["post_rock", "atmospheric", "ambient", "reverb_drenched"],
        "description": [
            "Clean arpeggios with layered delays creating spacious texture",
            "Reverb-drenched ambient swells building emotional crescendos",
            "Mid-tempo atmospheric passages with gentle dynamics"
        ]
    }
    song_style = result2.get("tags", [])
    guitar_features = result2.get("description", [])
    
    print(f"\n步骤2 - LLM生成:")
    print(f"  标签: {song_style}")
    print(f"  描述: {guitar_features[0][:60]}...")
    
    # 步骤3：【RAG集成点】使用生成的标签和描述进行检索
    print(f"\n步骤3 - RAG检索（基于生成的标签和描述）:")
    rag_context = integrate_rag_with_existing_system(
        chat_message=chat_message,
        song_style=song_style,
        guitar_features=guitar_features,
        memoryEnabled="true"
    )
    
    # 2. 在生成参数时使用 RAG 上下文
    if rag_context:
        print(f"\n  ✓ RAG检索成功")
        print(f"  - 音乐知识: {len(rag_context['music_context'])} 条")
        print(f"  - 参数推荐: {len(rag_context['parameter_recommendations'])} 个")
        
        # 显示推荐预设
        if rag_context['parameter_recommendations']:
            print(f"\n  推荐的参数预设:")
            for i, rec in enumerate(rag_context['parameter_recommendations'][:3], 1):
                print(f"    {i}. {rec['preset_name']}")
                print(f"       相似度: {rec['similarity']:.3f}, 评分: {rec['user_rating']}")
        
        # 3. 增强系统提示词
        print(f"\n步骤4 - 增强参数生成提示词:")
        original_prompt = "You are an audio effects parameter generator..."
        enhanced_prompt = enhance_system_prompt_with_rag(original_prompt, rag_context)
        print(f"  原始提示词长度: {len(original_prompt)} 字符")
        print(f"  增强后长度: {len(enhanced_prompt)} 字符")
        print(f"\n  RAG增强内容预览:")
        print(rag_context['rag_enhanced_prompt'][:300] + "...")
        
        # 4. 将新参数添加到 RAG（在生成参数后）
        print(f"\n步骤5 - 参数生成后添加到RAG:")
        if RAG_AVAILABLE:
            rag = AudioRAGSystem(api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", ""))
            example_parameters = {
                "ReverbOn": {"Size": 0.75, "Mix": 0.45},
                "DelayOn": {"Delay": 380, "Feedback": 0.35, "Mix": 0.30}
            }
            add_preset_to_rag(
                rag_system=rag,
                preset_name=chat_message,
                parameters=example_parameters,
                style_tags=song_style,
                features=guitar_features,
                user_rating="accept"
            )
            print(f"  ✓ 预设已保存到RAG知识库")
    
    print(f"\n=== 工作流程完成 ===")


if __name__ == "__main__":
    print("=== RAG Integration Module ===")
    print(f"RAG Available: {RAG_AVAILABLE}")
    
    if RAG_AVAILABLE:
        example_integration()
    else:
        print("\nTo enable RAG integration, install required packages:")
        print("pip install chromadb")
