from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import asyncio
import boto3
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from langgraph.graph import StateGraph

async def run_langgraph_agent(query: str):
    import yfinance as yf

    async def retrieve_realtime_stock_price(symbol: str):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            latest_price = data["Close"].iloc[-1]
            return {"tool": "retrieve_realtime_stock_price", "symbol": symbol.upper(), "latest_price": f"${latest_price:.2f}"}
        except Exception as e:
            return {"tool": "retrieve_realtime_stock_price", "symbol": symbol.upper(), "error": str(e)}

    async def retrieve_historical_stock_price(symbol: str, start_date: str, end_date: str):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            if data.empty:
                return {"tool": "retrieve_historical_stock_price", "symbol": symbol.upper(), "error": "No historical data found."}
            summary = data["Close"].describe()
            return {
                "tool": "retrieve_historical_stock_price",
                "symbol": symbol.upper(),
                "start_date": start_date,
                "end_date": end_date,
                "min": f"${summary['min']:.2f}",
                "max": f"${summary['max']:.2f}",
                "mean": f"${summary['mean']:.2f}"
            }
        except Exception as e:
            return {"tool": "retrieve_historical_stock_price", "symbol": symbol.upper(), "error": str(e)}

    async def plan_tool_calls(state):
        bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
        prompt = f"""
You are an AI agent that receives user questions about stocks. Respond in JSON format listing what tools to use and their arguments.

Available tools:
- retrieve_realtime_stock_price(symbol)
- retrieve_historical_stock_price(symbol, start_date, end_date)

Example output:
{{"tools": [{{"name": "retrieve_realtime_stock_price", "args": {{"symbol": "AAPL"}}}}]}}

User Query: {state['query']}
""" 
        try:
            response = bedrock.invoke_model(
                modelId="anthropic.claude-v2",
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"prompt": prompt, "max_tokens_to_sample": 300, "temperature": 0.3})
            )
            result = json.loads(response["body"].read().decode())
        except Exception as e:
            print("Failed to call Bedrock")
            return {"error": f"Failed to call Bedrock: {str(e)}"}
        try:
            tools = json.loads(result.get("completion", ""))
        except json.JSONDecodeError:
            tools = {}
        return {"query": state["query"], "tools": tools}

    async def run_tools(state):
        tasks = []
        for tool in state.get("tools", {}).get("tools", []):
            name = tool.get("name")
            args = tool.get("args", {})
            if name == "retrieve_realtime_stock_price" and "symbol" in args:
                tasks.append(retrieve_realtime_stock_price(args["symbol"]))
            elif name == "retrieve_historical_stock_price" and all(k in args for k in ("symbol", "start_date", "end_date")):
                tasks.append(retrieve_historical_stock_price(args["symbol"], args["start_date"], args["end_date"]))
        tool_outputs = await asyncio.gather(*tasks)
        return {"query": state["query"], "tools": state["tools"], "results": tool_outputs}

    async def summarize(state):
        bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
        tool_output_summary = json.dumps(state.get("results", []))
        prompt = f"""
The user asked the following question:

"{state['query']}"

Here are the results from calling the relevant tools in JSON format:

{tool_output_summary}

Write a clear, user-friendly answer based on the above.
"""
        try:
            response = bedrock.invoke_model(
                modelId="anthropic.claude-v2",
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"prompt": prompt, "max_tokens_to_sample": 200, "temperature": 0.5})
            )
            body = json.loads(response["body"].read().decode())
        except Exception as e:
            return {"error": f"Failed to call Bedrock: {str(e)}"}
        return {"response": body.get("completion", "Failed to generate final response.")}

    builder = StateGraph(dict)
    builder.add_node("plan", plan_tool_calls)
    builder.add_node("run", run_tools)
    builder.add_node("respond", summarize)
    builder.set_entry_point("plan")
    builder.add_edge("plan", "run")
    builder.add_edge("run", "respond")
    graph = builder.compile()

    async def response_generator():
        yield f"Processing query: {query}"
        result = await graph.invoke({"query": query})
        yield result.get("response", "No response generated.")

    return response_generator()

@app.get("/query")
async def query_stock(request: Request):
    q = request.query_params.get("q")
    print('query:'+ q)
    return StreamingResponse(await run_langgraph_agent(q), media_type="text/plain")

handler = Mangum(app)
