# Test complet

from tests_prompts import ALL_TEST_PROMPTS
from engine import HospitalRAGEngine

engine = HospitalRAGEngine()

for prompt in ALL_TEST_PROMPTS:
    response = engine.query(prompt.query)
    print(f"{prompt.query}: {'SAFE' if response.is_safe else 'BLOCKED'}")



