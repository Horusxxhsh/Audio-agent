"""
RAG 系统使用示例和测试脚本
Demonstrates how to use the RAG system with the existing Audio-agent project
"""

import sys
import json
from rag_system import AudioRAGSystem, initialize_knowledge_base
from rag_integration import integrate_rag_with_existing_system, add_preset_to_rag


def test_rag_basic():
    """测试基本的 RAG 功能"""
    print("=" * 60)
    print("测试 1: RAG 系统基本功能")
    print("=" * 60)
    
    # 初始化 RAG 系统
    rag = AudioRAGSystem(
        api_key="sk-1b73586fde854a329ec187dc371f53ef",
        base_url="https://api.deepseek.com"
    )
    
    # 初始化知识库
    initialize_knowledge_base(rag)
    
    # 查看统计信息
    stats = rag.get_collection_stats()
    print(f"\n知识库统计:")
    print(f"- 音乐知识条目: {stats['music_knowledge_count']}")
    print(f"- 参数预设条目: {stats['parameter_presets_count']}")
    
    # 测试检索
    print("\n\n测试检索功能:")
    print("-" * 60)
    query = "I want atmospheric guitar with lots of reverb"
    results = rag.retrieve_similar_knowledge(query, n_results=3, collection_type="music")
    
    for i, result in enumerate(results, 1):
        print(f"\n[检索结果 {i}]")
        print(f"相似度: {1 - result.get('distance', 1):.3f}")
        print(f"内容: {result['document'][:200]}...")


def test_rag_with_parameters():
    """测试参数预设功能"""
    print("\n\n" + "=" * 60)
    print("测试 2: 参数预设添加和检索")
    print("=" * 60)
    
    rag = AudioRAGSystem(
        api_key="sk-1b73586fde854a329ec187dc371f53ef",
        base_url="https://api.deepseek.com"
    )
    
    # 添加示例参数预设
    example_presets = [
        {
            "preset_name": "Atmospheric Post-Rock",
            "parameters": {
                "ReverbOn": {"Size": 0.75, "Damping": 0.45, "Width": 0.85, "Mix": 0.50},
                "DelayOn": {"Delay": 380.0, "Feedback": 0.40, "Mix": 0.35},
                "CompressorOn": {"Threshold": -18.0, "Ratio": 3.5, "Attack": 0.015, "Release": 0.200, "Makeup": 6.0, "Mix": 0.70},
                "EqualiserOn": {"100hz": -1.0, "200hz": 0.0, "800hz": 1.5, "3200hz": 2.5, "6400hz": 2.0}
            },
            "style_tags": ["post_rock", "atmospheric", "ambient"],
            "description": "Lush atmospheric tones with reverb and delay. Clean to mid-gain with ambient swells.",
            "user_rating": "accept"
        },
        {
            "preset_name": "Heavy Metal Rhythm",
            "parameters": {
                "DriverOn": {"Distortion": 0.85, "Volume": -15.0},
                "CompressorOn": {"Threshold": -24.0, "Ratio": 6.0, "Attack": 0.005, "Release": 0.120, "Makeup": 8.0, "Mix": 0.90},
                "EqualiserOn": {"100hz": -3.0, "200hz": -2.0, "800hz": 2.0, "3200hz": 3.0, "6400hz": 2.5}
            },
            "style_tags": ["metal", "heavy", "aggressive"],
            "description": "Tight high-gain rhythm tone for palm-muted riffs. Heavy compression and presence boost.",
            "user_rating": "accept"
        },
        {
            "preset_name": "Blues Lead",
            "parameters": {
                "ScreamerOn": {"Drive": 0.65, "Tone": 0.55, "Level": -10.0},
                "ReverbOn": {"Size": 0.35, "Damping": 0.50, "Width": 0.65, "Mix": 0.25},
                "DelayOn": {"Delay": 280.0, "Feedback": 0.30, "Mix": 0.22},
                "CompressorOn": {"Threshold": -20.0, "Ratio": 3.0, "Attack": 0.012, "Release": 0.180, "Makeup": 5.0, "Mix": 0.65}
            },
            "style_tags": ["blues", "expressive", "lead"],
            "description": "Warm mid-gain lead tone with natural compression. Subtle reverb and delay for sustain.",
            "user_rating": "accept"
        }
    ]
    
    # 添加预设到 RAG
    for preset in example_presets:
        rag.add_parameter_preset(**preset)
    
    print(f"\n已添加 {len(example_presets)} 个参数预设")
    
    # 测试参数推荐
    print("\n\n测试参数推荐:")
    print("-" * 60)
    recommendations = rag.recommend_parameters(
        style_tags=["atmospheric", "ambient"],
        user_description="I want spacious guitar sounds with reverb",
        n_recommendations=2
    )
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n[推荐 {i}] {rec['preset_name']}")
        print(f"相似度: {rec['similarity']:.3f}")
        print(f"风格标签: {rec['style_tags']}")
        print(f"用户评价: {rec['user_rating']}")
        print(f"参数示例: {list(rec['parameters'].keys())}")


def test_rag_generation():
    """测试 RAG 生成功能"""
    print("\n\n" + "=" * 60)
    print("测试 3: RAG 增强生成")
    print("=" * 60)
    
    rag = AudioRAGSystem(
        api_key="sk-1b73586fde854a329ec187dc371f53ef",
        base_url="https://api.deepseek.com"
    )
    
    # 确保知识库已初始化
    stats = rag.get_collection_stats()
    if stats['music_knowledge_count'] == 0:
        initialize_knowledge_base(rag)
    
    # 使用 RAG 生成分析
    print("\n查询: 如何创建 shoegaze 风格的吉他音色?")
    print("-" * 60)
    
    response = rag.generate_with_rag(
        user_query="How to create shoegaze guitar tone?",
        style_tags=["shoegaze", "dreamy", "reverb"],
        context_type="both",
        n_context=2
    )
    
    print(f"\nRAG 增强回答:\n{response}")


def test_integration_workflow():
    """测试完整的集成工作流程 - V2 修正版"""
    print("\n\n" + "=" * 60)
    print("测试 4: 完整集成工作流程（修正版）")
    print("=" * 60)
    print("模拟实际 llm.py 的工作流程")
    
    # 步骤1：用户原始输入
    chat_message = "atmospheric post-rock guitar with reverb"
    print(f"\n【步骤1】用户输入: {chat_message}")
    
    # 步骤2：模拟 LLM 生成标签和描述
    # 在实际系统中，这是 response2 的结果
    print(f"\n【步骤2】LLM分析用户输入，生成标签和描述...")
    song_style = ["post_rock", "atmospheric", "ambient", "reverb_drenched"]
    guitar_features = [
        "Clean arpeggios with layered delays creating spacious texture",
        "Reverb-drenched ambient swells building emotional crescendos",
        "Mid-tempo atmospheric passages with gentle dynamics"
    ]
    
    print(f"  生成的标签: {song_style}")
    print(f"  生成的描述: {guitar_features[0][:60]}...")
    
    # 步骤3：【RAG集成点】使用生成的标签和描述进行检索
    print(f"\n【步骤3】使用生成的标签和描述进行 RAG 检索...")
    rag_context = integrate_rag_with_existing_system(
        chat_message=chat_message,
        song_style=song_style,
        guitar_features=guitar_features,
        memoryEnabled="true"
    )
    
    if rag_context:
        print("\n✓ RAG 检索成功")
        print(f"  - 音乐知识条目: {len(rag_context['music_context'])}")
        print(f"  - 参数推荐: {len(rag_context['parameter_recommendations'])}")
        print(f"  - 检索查询: {rag_context.get('search_query', 'N/A')[:80]}...")
        
        # 显示推荐参数
        if rag_context['parameter_recommendations']:
            print("\n  推荐的参数预设（按相似度和评分排序）:")
            for i, rec in enumerate(rag_context['parameter_recommendations'][:3], 1):
                print(f"    {i}. {rec['preset_name']}")
                print(f"       相似度: {rec['similarity']:.3f}, 用户评分: {rec['user_rating']}")
        
        # 显示 RAG 增强提示词片段
        if rag_context.get('rag_enhanced_prompt'):
            print(f"\n  RAG 增强提示词片段（前300字符）:")
            print(f"    {rag_context['rag_enhanced_prompt'][:300]}...")
        
        # 步骤4：模拟参数生成（使用RAG上下文）
        print(f"\n【步骤4】基于 RAG 上下文生成参数...")
        from rag_integration import enhance_system_prompt_with_rag
        
        original_prompt = "You are an audio effects parameter generator. Generate parameters based on style tags."
        enhanced_prompt = enhance_system_prompt_with_rag(original_prompt, rag_context)
        
        print(f"  原始提示词长度: {len(original_prompt)} 字符")
        print(f"  RAG增强后长度: {len(enhanced_prompt)} 字符")
        print(f"  增加了: {len(enhanced_prompt) - len(original_prompt)} 字符的上下文")
        
        # 步骤5：模拟生成参数后添加到 RAG
        print(f"\n【步骤5】参数生成完成，添加到 RAG 知识库...")
        rag = AudioRAGSystem(api_key="sk-1b73586fde854a329ec187dc371f53ef")
        
        generated_parameters = {
            "ReverbOn": {"Size": 0.70, "Damping": 0.40, "Width": 0.80, "Mix": 0.45},
            "DelayOn": {"Delay": 360.0, "Feedback": 0.38, "Mix": 0.32},
            "CompressorOn": {"Threshold": -20.0, "Ratio": 3.2, "Attack": 0.018, "Release": 0.220}
        }
        
        add_preset_to_rag(
            rag_system=rag,
            preset_name=chat_message,
            parameters=generated_parameters,
            style_tags=song_style,  # 使用LLM生成的标签
            features=guitar_features,  # 使用LLM生成的描述
            user_rating="accept"
        )
        
        print("✓ 新参数已添加到 RAG 知识库（使用LLM生成的标签和描述）")
        print(f"\n工作流程总结:")
        print(f"  用户输入 → LLM生成标签 → RAG检索 → 增强提示词 → 生成参数 → 保存到RAG")


def interactive_test():
    """交互式测试"""
    print("\n\n" + "=" * 60)
    print("交互式 RAG 测试")
    print("=" * 60)
    print("\n输入您的查询，或输入 'quit' 退出")
    
    rag = AudioRAGSystem(
        api_key="sk-1b73586fde854a329ec187dc371f53ef",
        base_url="https://api.deepseek.com"
    )
    
    # 确保知识库已初始化
    stats = rag.get_collection_stats()
    if stats['music_knowledge_count'] == 0:
        print("\n正在初始化知识库...")
        initialize_knowledge_base(rag)
    
    while True:
        try:
            query = input("\n> 您的查询: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                print("退出测试")
                break
            
            if not query:
                continue
            
            # 简单的风格标签提取
            style_keywords = {
                'metal': ['metal', 'heavy', 'aggressive'],
                'post_rock': ['post', 'rock', 'atmospheric'],
                'blues': ['blues', 'expressive'],
                'ambient': ['ambient', 'atmospheric', 'spacey'],
                'shoegaze': ['shoegaze', 'dreamy', 'wall']
            }
            
            detected_styles = []
            query_lower = query.lower()
            for style, keywords in style_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    detected_styles.append(style)
            
            if not detected_styles:
                detected_styles = ['general']
            
            print(f"检测到的风格: {detected_styles}")
            
            # 检索相关知识
            results = rag.retrieve_similar_knowledge(query, n_results=2)
            if results:
                print("\n相关知识:")
                for i, result in enumerate(results, 1):
                    print(f"  [{i}] {result['document'][:150]}...")
            
            # 推荐参数
            recommendations = rag.recommend_parameters(
                style_tags=detected_styles,
                user_description=query,
                n_recommendations=2
            )
            
            if recommendations:
                print("\n参数推荐:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  [{i}] {rec['preset_name']} (相似度: {rec['similarity']:.3f})")
        
        except KeyboardInterrupt:
            print("\n\n退出测试")
            break
        except Exception as e:
            print(f"错误: {e}")


def main():
    """主函数 - 运行所有测试"""
    print("\n")
    print("=" * 60)
    print("  Audio-Agent RAG 系统测试套件")
    print("=" * 60)
    
    try:
        # 运行测试
        test_rag_basic()
        test_rag_with_parameters()
        test_rag_generation()
        test_integration_workflow()
        
        # 提供交互式测试选项
        print("\n\n" + "=" * 60)
        response = input("是否进行交互式测试? (y/n): ").strip().lower()
        if response == 'y':
            interactive_test()
        
        print("\n\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
