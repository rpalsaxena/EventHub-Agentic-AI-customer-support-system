"""
Configuration for EventHub Data Generation

Contains:
- AWS Bedrock client setup
- Data generation counts
- Model settings
- Helper functions
"""

import os
import json
from typing import Dict, Any, List
import boto3
from pathlib import Path

# ============================================
# PATHS
# ============================================

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"

# Create directories if they don't exist
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Output files
OUTPUT_FILES = {
    "users": GENERATED_DIR / "users.jsonl",
    "venues": GENERATED_DIR / "venues.jsonl",
    "events": GENERATED_DIR / "events.jsonl",
    "reservations": GENERATED_DIR / "reservations.jsonl",
    "kb_articles": GENERATED_DIR / "kb_articles.jsonl",
    "tickets": GENERATED_DIR / "tickets.jsonl",
}

# ============================================
# DATA COUNTS
# ============================================

DATA_COUNTS = {
    "users": 10_000,
    "venues": 50,
    "events": 500,
    "reservations": 50_000,
    "kb_articles": 100,
    "tickets": 5_000,
}

# Batch sizes for LLM generation (to manage token limits)
BATCH_SIZES = {
    "users": 50,        # Generate 50 users per LLM call
    "venues": 10,       # Generate 10 venues per LLM call
    "events": 20,       # Generate 20 events per LLM call
    "kb_articles": 5,   # Generate 5 articles per LLM call
    "tickets": 25,      # Generate 25 tickets per LLM call
}

# ============================================
# AWS BEDROCK CONFIG
# ============================================

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Available models (uncomment one to use)
AVAILABLE_MODELS = {
    # Anthropic Claude models
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",      # Good quality, slower
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",    # Best quality, slowest
    
    # Mistral models (fast!)
    "mistral-7b": "mistral.mistral-7b-instruct-v0:2",                # Very fast, good quality
    "mistral-large": "mistral.mistral-large-2402-v1:0",              # Better quality, slower
    "mixtral-8x7b": "mistral.mixtral-8x7b-instruct-v0:1",            # Good balance
    
    # Meta Llama models
    "llama3-8b": "meta.llama3-8b-instruct-v1:0",                     # Fast, good quality
    "llama3-70b": "meta.llama3-70b-instruct-v1:0",                   # Better quality, slower
    
    # Amazon Titan models (fastest, cheapest)
    "titan-lite": "amazon.titan-text-lite-v1",                       # Fastest, basic quality
    "titan-express": "amazon.titan-text-express-v1",                 # Fast, decent quality
}

# Select active model here
ACTIVE_MODEL = "mistral-7b"  # ⚡ Fast and good quality
MODEL_ID = AVAILABLE_MODELS[ACTIVE_MODEL]

# Model parameters
MODEL_PARAMS = {
    "max_tokens": 4096,
    "temperature": 0.7,      # Some creativity for realistic data
    "top_p": 0.9,
}

# ============================================
# BEDROCK CLIENT
# ============================================

def get_bedrock_client():
    """Get AWS Bedrock runtime client."""
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION,
    )

# ============================================
# LLM HELPER FUNCTIONS
# ============================================

def invoke_model(prompt: str, system_prompt: str | None = None) -> str:
    """
    Invoke LLM via AWS Bedrock (supports Claude, Mistral, Llama, Titan).
    
    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        
    Returns:
        Model response text
    """
    client = get_bedrock_client()
    
    # Determine model family from MODEL_ID
    if "anthropic" in MODEL_ID:
        # Claude format
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MODEL_PARAMS["max_tokens"],
            "temperature": MODEL_PARAMS["temperature"],
            "top_p": MODEL_PARAMS["top_p"],
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt
            
    elif "mistral" in MODEL_ID or "mixtral" in MODEL_ID:
        # Mistral format
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        body = {
            "prompt": f"<s>[INST] {full_prompt} [/INST]",
            "max_tokens": MODEL_PARAMS["max_tokens"],
            "temperature": MODEL_PARAMS["temperature"],
            "top_p": MODEL_PARAMS["top_p"],
        }
        
    elif "meta.llama" in MODEL_ID:
        # Llama format
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        body = {
            "prompt": full_prompt,
            "max_gen_len": MODEL_PARAMS["max_tokens"],
            "temperature": MODEL_PARAMS["temperature"],
            "top_p": MODEL_PARAMS["top_p"],
        }
        
    elif "amazon.titan" in MODEL_ID:
        # Titan format
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        body = {
            "inputText": full_prompt,
            "textGenerationConfig": {
                "maxTokenCount": MODEL_PARAMS["max_tokens"],
                "temperature": MODEL_PARAMS["temperature"],
                "topP": MODEL_PARAMS["top_p"],
            }
        }
    else:
        raise ValueError(f"Unsupported model: {MODEL_ID}")
    
    # Invoke model
    response = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
    )
    
    # Parse response based on model
    response_body = json.loads(response["body"].read())
    
    if "anthropic" in MODEL_ID:
        return response_body["content"][0]["text"]
    elif "mistral" in MODEL_ID or "mixtral" in MODEL_ID:
        return response_body["outputs"][0]["text"]
    elif "meta.llama" in MODEL_ID:
        return response_body["generation"]
    elif "amazon.titan" in MODEL_ID:
        return response_body["results"][0]["outputText"]
    else:
        raise ValueError(f"Cannot parse response for model: {MODEL_ID}")


# Alias for backward compatibility
def invoke_claude(prompt: str, system_prompt: str | None = None) -> str:
    """Backward compatible alias for invoke_model."""
    return invoke_model(prompt, system_prompt)


def invoke_claude_json(prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
    """
    Invoke Claude and parse JSON response.
    
    Args:
        prompt: User prompt (should ask for JSON output)
        system_prompt: Optional system prompt
        
    Returns:
        Parsed JSON as dictionary
    """
    response = invoke_claude(prompt, system_prompt)
    
    # Try to extract JSON from response
    try:
        # Handle case where response is wrapped in ```json ... ```
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
        
        return json.loads(json_str)
    
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response was: {response[:500]}...")
        raise


def invoke_claude_json_list(prompt: str, system_prompt: str | None = None) -> List[Dict[str, Any]]:
    """
    Invoke Claude and parse JSON array response.
    
    Args:
        prompt: User prompt (should ask for JSON array output)
        system_prompt: Optional system prompt
        
    Returns:
        Parsed JSON as list of dictionaries
    """
    result = invoke_claude_json(prompt, system_prompt)
    
    # Handle if result is wrapped in a key
    if isinstance(result, dict):
        # Try common keys
        for key in ["data", "items", "results", "users", "events", "venues", "articles", "tickets"]:
            if key in result:
                return result[key]
        # Return first list found
        for value in result.values():
            if isinstance(value, list):
                return value
    
    if isinstance(result, list):
        return result
    
    raise ValueError(f"Expected list, got {type(result)}")


# ============================================
# FILE HELPERS
# ============================================

def save_to_jsonl(data: List[Dict], filepath: Path) -> None:
    """
    Save list of dictionaries to JSONL file.
    
    Args:
        data: List of dictionaries to save
        filepath: Output file path
    """
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"✅ Saved {len(data)} records to {filepath}")


def append_to_jsonl(data: List[Dict], filepath: Path) -> None:
    """
    Append list of dictionaries to JSONL file.
    
    Args:
        data: List of dictionaries to append
        filepath: Output file path
    """
    with open(filepath, "a", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def load_from_jsonl(filepath: Path) -> List[Dict]:
    """
    Load list of dictionaries from JSONL file.
    
    Args:
        filepath: Input file path
        
    Returns:
        List of dictionaries
    """
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def clear_file(filepath: Path) -> None:
    """Clear/create empty file."""
    with open(filepath, "w", encoding="utf-8") as f:
        pass


# ============================================
# PROGRESS HELPER
# ============================================

def print_progress(current: int, total: int, entity: str) -> None:
    """Print progress bar."""
    percent = (current / total) * 100
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r{entity}: [{bar}] {current}/{total} ({percent:.1f}%)", end="", flush=True)
    if current == total:
        print()  # New line when complete

