from openai import OpenAI

client = OpenAI(
    base_url="https://ymatics.com/ai_sec/vllms/v1",
    api_key="EMPTY",
)

MODEL = "cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit"

messages = [
    {"role": "system", "content": "You are a helpful assistant. 한국어로 답변해주세요."}
]

print("=== vLLM 채팅 (quit 입력 시 종료) ===\n")

while True:
    user_input = input("나: ").strip()
    if not user_input:
        continue
    if user_input.lower() == "quit":
        print("채팅을 종료합니다.")
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    reply = response.choices[0].message.content
    print(f"\nAI: {reply}\n")

    messages.append({"role": "assistant", "content": reply})
