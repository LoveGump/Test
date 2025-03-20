""""
    math.csv ----> deepseek_math.json

    
"""



import json
import csv
import time
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
from openai._exceptions import APIError, RateLimitError, AuthenticationError, APIConnectionError

# 加载环境变量
load_dotenv()

# 初始化 DeepSeek 客户端
try:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("错误：未找到 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)
        
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )
except Exception as e:
    print(f"初始化 DeepSeek 客户端失败: {str(e)}")
    sys.exit(1)

def call_api(question):
    """调用 DeepSeek API 解析问题"""
    system_prompt = """
    The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format. 

    EXAMPLE INPUT: 
    Which is the highest mountain in the world? Mount Everest.

    EXAMPLE JSON OUTPUT:
    {
        "question": "Which is the highest mountain in the world?",
        "answer": "Mount Everest"
    }
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content":  question}
    ]
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                response_format={
                    'type': 'json_object'
                }
            )   
            
            # 获取响应内容
            content = response.choices[0].message.content
            
            # 尝试修复常见的JSON错误，如无效的转义字符
            content = content.replace("\\", "\\\\")  # 确保所有反斜杠被正确转义
            # 确保内容是有效的JSON格式
            try:
                parsed = json.loads(content)
                print("解析成功:", parsed)
                return parsed
            except json.JSONDecodeError:
                # 如果仍然无法解析，尝试更强的清理
                print("尝试替代解析方法...")
                # 创建一个基本结构，包含原始响应
                return {"question": question, "answer": content, "raw_response": True}
        
        except AuthenticationError as e:
            print(f"认证错误: API密钥可能无效或已过期 - {str(e)}")
            return {"question": question, "answer": "", "error": "认证错误"}
        except RateLimitError as e:
            print(f"请求频率限制: API请求过于频繁 - {str(e)}，等待重试... ({retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(5)  # 增加更长的等待时间
        except APIConnectionError as e:
            print(f"连接错误: 无法连接到 DeepSeek API - {str(e)}，等待重试... ({retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(2)
        except APIError as e:
            print(f"API错误: DeepSeek API返回错误 - {str(e)}，等待重试... ({retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(2)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: 无法解析API响应 - {str(e)}，等待重试... ({retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(2)
        except Exception as e:
            print(f"未知错误: {str(e)}，等待重试... ({retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(2)
    
    # 请求失败时返回空答案和错误信息
    return {"question": question, "answer": "", "error": "API调用失败，超过最大重试次数"}

def load_existing_results(json_path):
    """加载已有的 JSON 结果文件"""
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as json_file:
                return json.load(json_file)
        except Exception as e:
            print(f"读取现有JSON文件出错: {str(e)}，将创建新文件")
    return []

def save_result(result, json_path):
    """保存单个结果到 JSON 文件"""
    results = load_existing_results(json_path)
    
    # 确保result是字典类型
    if not isinstance(result, dict):
        print(f"警告: 结果不是字典类型，转换为字典: {result}")
        result = {"question": "未知问题", "answer": str(result), "error": "结果格式错误"}
    
    results.append(result)
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(results, json_file, ensure_ascii=False, indent=4)
    return len(results)

def save_checkpoint(index):
    """保存当前处理进度"""
    checkpoint_file = 'process_checkpoint.json'
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump({'last_index': index}, f)
    print(f"断点已保存：处理至第 {index} 个问题")

def load_checkpoint():
    """加载上次处理进度"""
    checkpoint_file = 'process_checkpoint.json'
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
                return checkpoint.get('last_index', 0)
        except Exception as e:
            print(f"读取断点文件出错: {str(e)}")
    return 0

def process_csv():
    """处理 CSV 文件中的问题并调用 API"""
    input_csv = 'math.csv'
    output_json = 'deepseek_math.json'
    
    try:
        if not os.path.exists(input_csv):
            print(f"错误: {input_csv} 文件不存在")
            return
        
        # 获取已处理的问题
        processed_questions = set()
        existing_results = load_existing_results(output_json)
        for item in existing_results:
            if isinstance(item, dict) and "question" in item:  # 确保item是字典且有question键
                processed_questions.add(item["question"])
        print(f"发现已有结果文件，包含 {len(processed_questions)} 个已处理问题")
        
        # 读取问题列表
        questions = []
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # 跳过标题行
            for row in reader:
                if row and len(row) > 0:
                    questions.append(row[0])
        print(f"从CSV读取了 {len(questions)} 个问题")
        
        # 加载断点，获取上次处理到的位置
        start_index = load_checkpoint()
        if start_index > 0:
            print(f"从断点恢复：从第 {start_index + 1} 个问题继续处理")
        
        # 处理每个问题
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        try:
            for i, question in enumerate(questions):
                # 跳过已经处理过的问题（基于索引）
                if i < start_index:
                    print(f"跳过已处理的问题 {i+1}/{len(questions)}: {question[:30]}...（基于断点）")
                    skipped_count += 1
                    continue
                
                # 跳过已处理的问题（基于问题内容）
                if question in processed_questions:
                    print(f"跳过已处理的问题 {i+1}/{len(questions)}: {question[:30]}...（已存在结果）")
                    skipped_count += 1
                    save_checkpoint(i + 1)  # 修正：更新断点为下一个位置
                    continue
                
                print(f"处理问题 {i+1}/{len(questions)}: {question[:30]}...")
                result = call_api(question)  # API返回的已经是结构化数据
                
                # 确保结果是字典
                if not isinstance(result, dict):
                    print(f"警告: API返回的结果不是字典类型，转换为字典")
                    result = {"question": question, "answer": str(result), "error": "API返回格式错误"}
                
                # 检查是否有错误
                if "error" in result:
                    error_count += 1
                    print(f"问题 {i+1} 处理出错: {result.get('error', '未知错误')}")
                
                # 立即保存结果，防止中断丢失数据
                total_saved = save_result(result, output_json)
                processed_count += 1
                print(f"问题 {i+1} 已处理并保存，当前共有 {total_saved} 个结果")
                
                # 修正：更新断点为下一个位置，而不是当前位置
                save_checkpoint(i + 1)
                
                # 更新已处理问题集合，防止在同一次运行中重复处理
                processed_questions.add(question)
                
                # 添加短暂延迟，避免请求过于频繁
                time.sleep(1)
                
            # 处理完成后删除断点文件
            checkpoint_file = 'process_checkpoint.json'
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
                print("处理完成，已清除断点文件")
                
        except KeyboardInterrupt:
            print("\n程序被用户中断，已保存断点。重启程序可从断点处继续。")
            return
        
        print(f"本次处理了 {processed_count} 个新问题，成功 {processed_count-error_count} 个，失败 {error_count} 个，跳过了 {skipped_count} 个已处理问题")
        print(f"所有结果已保存到 {output_json}")
    except Exception as e:
        print(f"处理CSV文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()  # 打印详细的错误跟踪

if __name__ == "__main__":
    process_csv()
