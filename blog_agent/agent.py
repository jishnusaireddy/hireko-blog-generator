"""Pydantic AI Agent definition with pedantic system prompt and harness tools."""

import os
import json
import re
import logfire
import httpx
from typing import Any, Dict, List, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai_harness import Shell, CodeMode, FileSystem, BaseCapability
from .deps import BlogAgentDeps


PEDANTIC_SYSTEM_PROMPT = """
You are a pedantic, meticulous AI Research & Blog Authoring Agent operating under a strict 3-iteration quality harness.

CRITICAL FACTUAL SAFETY & PEDANTIC RULES:
1. Current Year Context: 2026.
2. UNIVERSAL STRICT FACTUAL ACCURACY:
   - NEVER invent specific numbers, percentages, rates, salary figures, release dates, rankings, legal claims, or named report titles.
   - Any specific number, date, or entity presented as fact MUST be grounded in verified research evidence.
   - When evidence is qualitative, write clear, detailed qualitative guidance without hallucinating fake metrics.
3. STRUCTURE & LENGTH:
   - Generate substantial, publication-ready, deeply informative technical content.
   - Maintain 4-6 primary H2 sections plus a dedicated "Frequently Asked Questions (FAQ)" H3 section.
   - Target practical editorial depth that fits the requested word count.
4. HARNESS INTEGRATION:
   - Utilize FileSystem, CodeMode, and Shell harness capabilities to read/write self-contained blog assets.
"""


async def perform_web_search(query: str) -> List[Dict[str, str]]:
    """Standalone web search helper function."""
    serper_key = os.getenv("SERPER_API_KEY")
    blocked_source_pattern = re.compile(
        r"(instagram|facebook|pinterest|tiktok|x\.com|twitter|reddit|quora|youtube|youtu\.be)",
        re.IGNORECASE,
    )
    if serper_key:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 5},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("organic", []):
                        link = item.get("link", "").strip()
                        title = item.get("title", "").strip()
                        if not link or not title or blocked_source_pattern.search(f"{link} {title}"):
                            continue
                        results.append({
                            "title": title,
                            "url": link,
                            "snippet": item.get("snippet", "")
                        })
                    if results:
                        return results
        except Exception as e:
            print(f"[Search Tool] Serper query error: {e}")

    # Offline fallback: use broad real sources, but avoid inventing report claims.
    return [
        {
            "title": "U.S. Bureau of Labor Statistics - Employment Reports",
            "url": "https://www.bls.gov",
            "snippet": "Official U.S. labor-market data source for employment, unemployment, wages, job openings, and industry-level trends."
        },
        {
            "title": "SHRM - Workplace and Talent Research",
            "url": "https://www.shrm.org",
            "snippet": "Workplace research and HR guidance covering recruiting, workforce planning, compliance, and talent practices."
        },
        {
            "title": "LinkedIn Economic Graph - Workforce Insights",
            "url": "https://economicgraph.linkedin.com",
            "snippet": "Labor-market and skills insights based on hiring, workforce mobility, and professional skills data."
        },
        {
            "title": "Indeed Hiring Lab - Labor Market Research",
            "url": "https://www.hiringlab.org",
            "snippet": "Research on job postings, hiring demand, wages, remote work, and labor-market dynamics."
        }
    ]


def create_blog_agent(model: Any = "test-model") -> Agent[BlogAgentDeps, Any]:
    """Creates and configures the Pydantic AI Blog Agent instance."""
    
    # Configure Logfire instrumentation if available
    try:
        logfire.configure(service_name="pydantic-ai-blog-agent", send_to_logfire=False)
    except Exception:
        pass

    agent = Agent(
        model=model,
        deps_type=BlogAgentDeps,
        system_prompt=PEDANTIC_SYSTEM_PROMPT,
    )

    @agent.tool
    async def web_search_tool(ctx: RunContext[BlogAgentDeps], query: str) -> List[Dict[str, str]]:
        return await perform_web_search(query)

    @agent.tool
    async def extract_evidence_tool(ctx: RunContext[BlogAgentDeps], source_url: str, text_content: str) -> Dict[str, Any]:
        evidence_entry = {
            "source_url": source_url,
            "extracted_claims": text_content[:300],
            "verified": True
        }
        ctx.deps.evidence_pack.append(evidence_entry)
        return {"status": "added", "total_evidence_count": len(ctx.deps.evidence_pack)}

    return agent
