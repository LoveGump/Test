""""
# math.csv文件 ------> chat4o_math.json文件

"""

import http.client
import json
import csv
import time
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def call_api(question):
    conn = http.client.HTTPSConnection("api.chatanywhere.tech")
    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": question
            }
        ]
    })
    headers = {
        'Authorization': f'Bearer {os.getenv("API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn.request("POST", "/v1/chat/completions", payload, headers)
            res = conn.getresponse()
            data = res.read()
            response = json.loads(data.decode("utf-8"))
            
            # 检查是否有有效响应
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            else:
                print(f"KPI返回为空，等待重试... ({retry_count+1}/{max_retries})")
                retry_count += 1
                time.sleep(1)
        except Exception as e:
            print(f"请求出错: {str(e)}，等待重试... ({retry_count+1}/{max_retries})")
            retry_count += 1
            time.sleep(1)
    
    return "API调用失败，无法获取回答"

def save_result(result, json_path):
    """保存单个结果到JSON文件"""
    # 检查文件是否存在，如果存在则读取现有数据
    results = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as json_file:
                results = json.load(json_file)
        except Exception as e:
            print(f"读取现有JSON文件出错: {str(e)}，将创建新文件")
    
    # 添加新结果
    results.append(result)
    
    # 保存回文件
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(results, json_file, ensure_ascii=False, indent=4)
    
    return len(results)

def process_csv():
    # 检查文件是否存在
    if not os.path.exists('math.csv'):
        print("错误: math.csv文件不存在")
        return
    

#--------------------------------------------  # -------------------------------------------------------------------
    

    # 设置JSON文件路径
    json_path = 'chat4o_math.json'
    
    # 获取已处理的问题（如果有）
    processed_questions = set()
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as json_file:
                existing_results = json.load(json_file)
                for item in existing_results:
                    processed_questions.add(item["question"])
            print(f"发现已有结果文件，包含 {len(processed_questions)} 个已处理问题")
        except Exception as e:
            print(f"读取现有结果出错: {str(e)}")
    
    # 读取问题
    questions = []
    with open('math.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)  # 读取头行，如果有的话
        for row in reader:
            if row and len(row) > 0:
                questions.append(row[0])
    
    print(f"从CSV读取了 {len(questions)} 个问题")
    
    # 处理问题并保存回答
    processed_count = 0
    skipped_count = 0
    for i, question in enumerate(questions):
        # 跳过已处理的问题
        if question in processed_questions:
            print(f"跳过已处理的问题 {i+1}/{len(questions)}: {question[:30]}...")
            skipped_count += 1
            continue
        
        print(f"处理问题 {i+1}/{len(questions)}: {question[:30]}...")
        answer = call_api(question)
        
        # 创建结构化的结果
        result = {
            "question": question,
            "answer": answer,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 立即保存结果
        total_saved = save_result(result, json_path)
        processed_count += 1
        print(f"问题 {i+1} 已处理并保存，当前共有 {total_saved} 个结果")
    
    print(f"本次处理了 {processed_count} 个新问题，跳过了 {skipped_count} 个已处理问题")
    print(f"所有结果已保存到 {json_path}")

if __name__ == "__main__":
    process_csv()
    print("所有问题处理完成，结果已逐条保存到 test.json")