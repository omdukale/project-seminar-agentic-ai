import os
import asyncio
import json
import streamlit as st
from agents import Agent, Runner, FileSearchTool, ModelSettings, trace
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from agents.mcp import MCPServerStdio  
from dotenv import load_dotenv
from markdown import lra_to_markdown, format_retrieved_context, Citation, LegalResearchAnswer


load_dotenv(override=True)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PERPLEXITY_API_KEY = os.getenv("perplexity_api_key")
VECTOR_STORE_ID = 'vs_68ffd3098cfc8191bff58be73641ed16'


def build_retrieval_agent():
    retrieval_tool = FileSearchTool(
        vector_store_ids=[VECTOR_STORE_ID],
        max_num_results=5,
    )

    retrieval_agent = Agent(
        name="Retrieval Agent",
        instructions=(
            "Retrieve only verbatim, highly relevant passages from the legal corpus.\n"
            "- Prioritize: holdings/rulings > reasoning > statutes cited > analogous facts\n"
            "- Prefer Supreme Court; include case name, citation, date when present\n"
            "- No summaries or answers; output raw snippets with source metadata only\n"
            "- Maximize precision; fewer but on-point passages"
            ),
        model="gpt-4o-mini",
        tools=[retrieval_tool],
    )
    return retrieval_agent

def build_formulation_agent():
    formulation_agent = Agent(
        name="Formulation Agent",
        instructions=(
            "Synthesize a LegalResearchAnswer using ONLY the provided context.\n"
            "Follow IRAC and fill all fields:\n"
            "- issue: precise question of law\n"
            "- short_answer: 2–3 plain sentences, direct\n"
            "- rule: statutes/cases cited (exact sections/citations when present)\n"
            "- analysis: apply rule to query; use court reasoning; compare precedents\n"
            "- conclusion: final determination + implications\n"
            "- citations: all cases/statutes with brief relevance; mark SCC_citation for SC\n"
            "- judgement: overruled/distinguished/affirmed if stated\n"
            "- confidence_score: 0.0–1.0 based on context sufficiency\n"
            "Do not use external knowledge. Return only the schema object."
        ),
        model="gpt-4o-mini",
        output_type=LegalResearchAnswer,
    )
    return formulation_agent


async def run_verification_with_scoped_server(verification_input: str) -> LegalResearchAnswer:
    params = {
        "command": "npx",
        "args": ["-y", "server-perplexity-ask"],
        "env": {
            "PERPLEXITY_API_KEY": os.getenv("perplexity_api_key", ""),
        },
    }
    async with MCPServerStdio(params=params, client_session_timeout_seconds=30) as server:
        verification_agent = Agent(
            name="Verification Agent",
            instructions=(
                "Verify the analysis via MCP web search (mandatory).\n"
                "Check: case status (overruled/stayed/appealed), statutory amendments, recent SC rulings, citation accuracy.\n"
                "If updates found: adjust judgement, citations (add URLs), brief notes in analysis, and confidence_score.\n"
                "Do not change original reasoning unless contradicted by sources.\n"
                "Add web sources as citations: source_type 'article' or 'case', title, 'Web source - [site]', link, summary, SCC_citation=false.\n"
                "Return the updated LegalResearchAnswer. Tool use required."
            ),
            model="gpt-4o-mini",
            mcp_servers=[server],
            output_type=LegalResearchAnswer,
            model_settings=ModelSettings(tool_choice="required"),
        )
        v_res = await Runner.run(verification_agent, verification_input)
        return v_res.final_output

async def run_pipeline(user_query: str):
    
        retrieval_agent = build_retrieval_agent()
        with trace("Retrieval Agent Trace"):
            retrieved_context_res = await Runner.run(retrieval_agent, user_query)
        retrieved_context = retrieved_context_res.final_output

        formulation_agent = build_formulation_agent()
        input_for_formulation = (
        f"Query: {user_query}\n\n"
        f"Context:\n{retrieved_context}\n\n"
        "Synthesize LegalResearchAnswer per schema."
        )
        with trace("Formulation Agent Trace"):
            formulation_result = await Runner.run(formulation_agent, input_for_formulation)
        final_analysis: LegalResearchAnswer = formulation_result.final_output

        verification_input = (
        f"Query: {user_query}\n\n"
        f"Analysis:\n{final_analysis.model_dump_json(indent=2) if hasattr(final_analysis, 'model_dump_json') else str(final_analysis)}\n\n"
        "Task: Web-verify via MCP; update if needed; return LegalResearchAnswer."
        )
        try:
            with trace("Verification Agent Trace"):
                final_verified_analysis = await run_verification_with_scoped_server(verification_input)
            return retrieved_context, final_verified_analysis
        except Exception as e:
            print(f"Verification failed: {e}")
            return retrieved_context, final_analysis

def run_async(coro):
    """Run async coroutine in Streamlit's sync context."""
    return asyncio.run(coro)


st.set_page_config(page_title="Legal Research AI Assistant", page_icon="⚖️", layout="centered")

st.title("⚖️ Legal Research AI Assistant")
st.caption("Agentic Workflow (Retrieval → Formulation → Verification)")

with st.sidebar:
    st.header("⚙️ Settings")
    
    VECTOR_STORE_ID = st.text_input(
        "Vector Store ID",
        value=VECTOR_STORE_ID,
        type="default",
        help="Your OpenAI vector store ID for legal documents"
    )
    
    st.info("ℹ️ Verification via MCP web search is always ON.")
    
    st.divider()
    
    with st.expander("ℹ️ About"):
        st.markdown("""
        This app uses a multi-agent system:
        1. **Retrieval Agent**: Finds relevant case documents
        2. **Formulation Agent**: Analyzes and structures response
        3. **Verification Agent**: Fact-checks with live web search
        """)

query = st.text_area(
    "📝 Enter your legal research question:",
    height=120,
    placeholder="e.g., What was the court's ruling in the Wikimedia case?",
    help="Ask any question about Indian Supreme Court cases in your database"
)

st.markdown("---")

col1, col2, spacer = st.columns([2, 1, 1])
with col1:
    run_btn = st.button(
        "🚀 Run Analysis",
        type="primary",
        use_container_width=True,
        disabled=not query.strip(), 
        help="Click to start the legal research pipeline"
    )

with col2:
    clear_btn = st.button(
        "🗑️ Clear All",
        use_container_width=True,
        help="Clear the query and results"
    )

if clear_btn:
    st.session_state.clear()
    st.rerun()

if run_btn:
    if not VECTOR_STORE_ID:
        st.error("Please provide a valid VECTOR_STORE_ID in the sidebar before running.")
    elif not query.strip():
        st.error("Please enter a query.")
    else:
            with st.spinner("🔍 Running retrieval, formulation, and verification..."):
                retrieved_context, final_analysis = run_async(run_pipeline(query))
            
            with st.container():
                st.subheader("📄 Retrieved Context")
                st.markdown(format_retrieved_context(retrieved_context))
                
                with st.expander("🔧 Raw context (debug)"):
                    if isinstance(retrieved_context, (dict, list)):
                        st.code(json.dumps(retrieved_context, indent=2), language="json")
                    else:
                        st.code(str(retrieved_context))
                
                st.divider()
                
                with st.container():
                    st.subheader("⚖️ Final Analysis")
                    st.markdown(lra_to_markdown(final_analysis))
                    
                    with st.expander("🔧 Raw JSON (debug)"):
                        if isinstance(final_analysis, BaseModel):
                            st.code(final_analysis.model_dump_json(indent=2), language="json")
                        else:
                            try:
                                st.code(json.dumps(final_analysis, indent=2), language="json")
                            except Exception:
                                st.code(str(final_analysis))
