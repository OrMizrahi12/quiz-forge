import asyncio
import time
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.AsyncAnthropic()
limit = asyncio.Semaphore(3)
start = time.perf_counter()
TOPICS = ["HTTP status codes", "JSON", "REST", "TCP", "DNS", "TLS"]


async def ask(topic):
    async with limit:
        began = time.perf_counter()
        print(f"{began - start:5.2f} s  start  {topic}")
        message = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            messages=[{"role": "user", "content": f"Write one short quiz question about {topic}. Question only."}],
        )
        took = time.perf_counter() - began
        print(f"{time.perf_counter() - start:5.2f} s  done   {topic} ({took:.2f} s)")
        return took


async def main():
    times = await asyncio.gather(*(ask(topic) for topic in TOPICS))
    print(f"\n{len(times)} calls, {sum(times):.2f} s of waiting, {time.perf_counter() - start:.2f} s on the clock")


asyncio.run(main())
