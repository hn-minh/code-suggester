import asyncio
import json
import os
from pathlib import Path
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio
from configs.env import settings

OPENAI_API_KEY = settings.OPENAI_API_KEY
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SEMAPHORE = asyncio.Semaphore(5)

SYSTEM_PROMPT = """You are an expert AI Backend Engineer. 
Your task is to reverse-engineer a realistic user instruction (in English) that would generate the provided Python function.

Guidelines:
1. The instruction should be natural, detailed, and context-aware (e.g., mention FastAPI, SQLAlchemy, or Vector DBs if the code implies it).
2. Clearly state the requirements, input types, and expected output.
3. DO NOT include the actual code or the exact function name in your prompt. Frame it as a problem to be solved.
4. Output ONLY the user instruction text, without any conversational filler or formatting block."""

async def generate_instruction(func_code: str) -> str:
    async with SEMAPHORE:
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Generate a user prompt for this code:\n\n```python\n{func_code}\n```"}
                ],
                temperature=0.7,
                max_tokens=512
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return None

async def process_dataset(input_path: Path, output_path: Path):
    with open(input_path, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f]
        
    async def process_record(record):
        func_code = record['text']
        instruction = await generate_instruction(func_code)
        
        if instruction:
            return {
                "messages": [
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": func_code}
                ]
            }
        return None

    tasks = [process_record(r) for r in records]
    results = await tqdm_asyncio.gather(*tasks, desc="Generating Prompts")
    
    valid_dataset = [res for res in results if res is not None]

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in valid_dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"\n Done! Saved {len(valid_dataset)} Instruction-Response to {output_path}")

if __name__ == "__main__":
    input_file = Path("data/raw/ai_backend_dataset.jsonl")
    output_file = Path("data/processed/magicoder_instruct_dataset.jsonl")
    
    asyncio.run(process_dataset(input_file, output_file))

