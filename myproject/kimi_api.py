"""
 math.csv---->kimi_math.json

"""



import os
import csv
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def read_questions_from_csv(file_path):
    """Read questions from a CSV file."""
    questions = []
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        
        # Skip comment line and header
        for line in lines[2:]:  # Start from the third line
            line = line.strip()
            if line:  # Skip empty lines
                questions.append(line)
    
    return questions

def load_existing_answers(json_path):
    """Load existing answers from JSON file if it exists."""
    answers = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                results = json.load(file)
                for item in results:
                    answers[item["question"]] = item["answer"]
            print(f"Loaded {len(answers)} existing answers from {json_path}")
        except Exception as e:
            print(f"Error loading existing answers: {e}")
    return answers

def save_results(results, json_path):
    """Save results to JSON file."""
    try:
        with open(json_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving results to JSON: {e}")
        return False

def get_answer_from_kimi(client, question, max_retries=5, retry_delay=2):
    """Query the Kimi API for an answer, with retry mechanism and time limit."""
    total_wait_time = 0
    max_wait_time = 60  # Maximum cumulative wait time in seconds
    
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[
                    {"role": "system", "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。"},
                    {"role": "user", "content":   question}
                ],
                temperature=0.3,
            )
            return completion.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                # Check if it's a rate limit error (429)
                if hasattr(e, 'status_code') and e.status_code == 429:
                    wait_time = 10  # Wait 10 seconds for rate limit errors
                    print(f"Rate limit exceeded (429 error). Waiting {wait_time} seconds before retrying...")
                else:
                    wait_time = retry_delay
                    print(f"Error querying API: {e}. Retrying in {wait_time} seconds...")
                
                # Check if waiting would exceed our time limit
                if total_wait_time + wait_time > max_wait_time:
                    print(f"Would exceed maximum wait time of {max_wait_time}s. Giving up on this question.")
                    return f"Error: API request timed out after {total_wait_time}s of cumulative waiting - {str(e)}"
                
                total_wait_time += wait_time
                print(f"Total wait time so far: {total_wait_time}s")
                time.sleep(wait_time)
            else:
                print(f"Failed to get answer after {max_retries} attempts: {e}")
                return f"Error: Could not obtain answer from API - {str(e)}"

def main():
    # Load API key from environment
    api_key = os.getenv("KIMI_API_KEY")
    if not api_key:
        print("Error: KIMI_API_KEY not found in environment variables")
        return

    # Initialize client
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
    )
    
    # File paths
    csv_file_path = "math.csv"
    output_json_path = "kimi_math.json"
    
    # Load existing answers
    existing_answers = load_existing_answers(output_json_path)
    
    # Read questions
    try:
        questions = read_questions_from_csv(csv_file_path)
        print(f"Loaded {len(questions)} questions from CSV")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Get answers and build results
    results = []
    # First, add existing answers to results
    for question, answer in existing_answers.items():
        results.append({
            "question": question,
            "answer": answer
        })
    
    # Process questions that don't have answers yet
    for i, question in enumerate(questions):
        if question in existing_answers:
            print(f"Skipping question {i+1}/{len(questions)}: already answered")
            continue
            
        print(f"Processing question {i+1}/{len(questions)}: {question}")
        answer = get_answer_from_kimi(client, question)
        
        # Add to results
        results.append({
            "question": question,
            "answer": answer
        })
        
        # Save after each question
        print(f"Saving progress...")
        if save_results(results, output_json_path):
            print(f"Progress saved to {output_json_path}")
        
    print(f"All questions processed. Final results saved to {output_json_path}")

if __name__ == "__main__":
    main()
