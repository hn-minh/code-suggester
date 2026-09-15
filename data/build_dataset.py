import ast
import json
import re
from pathlib import Path
from datasketch import MinHash, MinHashLSH
from tqdm import tqdm

NUM_PERMUTATIONS = 128
LSH_THRESHOLD = 0.85

lsh = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERMUTATIONS)
seen_hashes = set()

def get_tokens(text):
    return set(re.findall(r'\b\w+\b', text.lower()))

def extract_functions_from_code(source_code):
    extracted = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return extracted

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = ast.get_docstring(node)
            if docstring and len(node.body) > 3:
                func_code = ast.unparse(node)
                extracted.append({
                    "name": node.name,
                    "docstring": docstring,
                    "code": func_code
                })
    return extracted

def process_and_dedup(file_paths, output_jsonl):
    dataset = []
    
    with open(output_jsonl, 'w', encoding='utf-8') as out_file:
        for path in tqdm(file_paths, desc="Processing Files"):
            try:
                content = Path(path).read_text(encoding='utf-8')
            except Exception:
                continue

            functions = extract_functions_from_code(content)
            
            for func in functions:
                tokens = get_tokens(func["code"])
                if not tokens:
                    continue
                    
                m = MinHash(num_perm=NUM_PERMUTATIONS)
                for token in tokens:
                    m.update(token.encode('utf-8'))
                
                result = lsh.query(m)
                
                if not result:
                    func_id = f"{path.name}_{func['name']}_{len(dataset)}"
                    lsh.insert(func_id, m)
                    
                    record = {
                        "messages": [
                            {"role": "user", "content": f"Write a function to: {func['docstring']}"},
                            {"role": "assistant", "content": func['code']}
                        ]
                    }
                    out_file.write(json.dumps(record, ensure_ascii=False) + '\n')
                    dataset.append(func_id)

    print(f"\n Done! Saved {len(dataset)} records")

if __name__ == "__main__":
    source_dir = Path("./raw_github_data") 
    all_py_files = list(source_dir.rglob("*.py"))
    
    process_and_dedup(all_py_files, "ai_backend_dataset.jsonl")
