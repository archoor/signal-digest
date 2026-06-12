from app.config import get_settings
from litellm import completion

s = get_settings()
print("model", s.llm_model, "base", s.llm_api_base, "key_set", bool(s.llm_api_key))
try:
    r = completion(
        model=s.llm_model,
        api_key=s.llm_api_key,
        api_base=s.llm_api_base,
        timeout=90,
        messages=[{"role": "user", "content": 'Reply JSON only: {"ok": true}' }],
        response_format={"type": "json_object"},
    )
    print("OK", r.choices[0].message.content)
except Exception as e:
    print("FAIL", type(e).__name__, e)
