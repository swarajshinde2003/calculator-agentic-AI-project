from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from agent.agentic_workflow import GraphBuilder
from langchain_core.messages import HumanMessage

load_dotenv()

app = FastAPI(
    title="Calculator",
    version= "1.0.0"
)

app.add_middleware(
    CORSMiddleware ,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

class QueryRequest(BaseModel):
    question : str
    
graph_builder = GraphBuilder()
react_app  = graph_builder.build()

@app.post("/query")
async def query_agent(query:QueryRequest):
    try :
        messages = {
            "messages" : [
                HumanMessage(content = query.question)
            ]
        }
        result  = react_app.invoke(messages)
        if isinstance(result , dict) and "messages" in result:
            final_answer = result["messages"][-1].content  
        else:
            final_answer  = str(result)
        return{
            "status" : "success",
            "answer" : final_answer
        }
    except Exception as exc :
        return JSONResponse(
            status_code=500,
            content={
                "status" : "error",
                "message" : str(exc)
            }
        )
