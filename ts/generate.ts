// Quiz Forge v0, the same call in TypeScript: count first, check the limit, stream, then usage, request id and cost.
// Run from ts/:  node --env-file=../.env generate.ts L1.3
import Anthropic from "@anthropic-ai/sdk";
import { readFileSync } from "node:fs";

const config = readFileSync("../config.toml", "utf8");
const pricing = readFileSync("../pricing.toml", "utf8");
const setting = (name: string) => config.match(new RegExp(`^${name}\\s*=\\s*"?([^"\\s#]+)`, "m"))![1];

const model = setting("writer");
const maxTokens = Number(setting("max_tokens"));
const limit = Number(setting("max_request_usd"));
const table = pricing.split(`[models."${model}"]`)[1];   // this model's prices, dollars per million tokens
const price = (name: string) => Number(table.match(new RegExp(`^${name}\\s*=\\s*([0-9.]+)`, "m"))![1]);

const lesson = process.argv[2] ?? "L1.3";
const text = readFileSync(`../${setting("path")}/${lesson}.md`, "utf8");
const system = "You write practice exam questions from course lesson notes. Use only facts stated in the lesson.";
const messages: Anthropic.MessageParam[] = [{
  role: "user",
  content: `Lesson ${lesson}:\n\n${text}\n\nWrite 2 multiple-choice practice questions about this lesson. For each one: ` +
    "the question, options A to D, the answer letter, and a one-line explanation that quotes the lesson.",
}];

const client = new Anthropic();
const counted = (await client.messages.countTokens({ model, system, messages })).input_tokens;
const most = (counted * price("input") + maxTokens * price("output")) / 1_000_000;
if (most > limit) throw new Error(`${lesson}: could cost $${most.toFixed(4)}, over the $${limit} limit`);

const stream = client.messages.stream({ model, max_tokens: maxTokens, system, messages });
stream.on("text", (chunk) => process.stdout.write(chunk));
const message = await stream.finalMessage();

const { input_tokens, output_tokens } = message.usage;
const cost = (input_tokens * price("input") + output_tokens * price("output")) / 1_000_000;
console.log(`\n\n${counted} counted, ${input_tokens} in, ${output_tokens} out, $${cost.toFixed(5)}, ${message.stop_reason}`);
console.log("request id:", stream.request_id ?? message._request_id);
