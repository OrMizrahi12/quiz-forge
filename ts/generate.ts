import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const message = await client.messages.create({
  model: "claude-haiku-4-5",
  max_tokens: 100,
  system: "You write quiz questions for developers.",
  messages: [
    { role: "user", content: "Write one quiz question about HTTP status codes. Reply with the question only." },
  ],
});

for (const block of message.content) {
  if (block.type === "text") console.log(block.text);
}
console.log("stop_reason:", message.stop_reason);
console.log("usage:", message.usage.input_tokens, "in,", message.usage.output_tokens, "out");
console.log("request id:", message._request_id);
