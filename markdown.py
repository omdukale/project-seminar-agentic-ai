from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Citation(BaseModel):
    source_type: Literal["case", "statute", "regulation", "treatise", "article", "other"]
    title: str
    citation: str
    jurisdiction: Optional[str] = None
    link: Optional[str] = None
    citation_summary: str
    SCC_citation: bool = Field(..., description="Whether the citation is from the SCC or not")

class LegalResearchAnswer(BaseModel):
    issue: str = Field(..., description="Clearly defined legal issue or question.")
    short_answer: str = Field(..., description="Concise, plain-language answer to the legal question.")
    rule: str = Field(..., description="Relevant legal rule(s), including statute or precedent.")
    analysis: str = Field(..., description="Detailed explanation applying the rule to the issue.")
    conclusion: str = Field(..., description="Final conclusion, considering all analysis.")
    citations: List[Citation] = Field(default_factory=list, description="Primary and secondary legal sources relied on.")
    judgement: Optional[str] = Field(None, description="Whether the judgement was overruled or not")
    confidence_score: float = Field(..., description="A score from 0.0 to 1.0 indicating confidence in the answer based on the clarity and completeness of the retrieved documents.")


def lra_to_markdown(lra) -> str:
    """Convert a LegalResearchAnswer to beautifully formatted Markdown."""
    if hasattr(lra, "model_dump"):
        d = lra.model_dump()
    elif hasattr(lra, "dict"):
        d = lra.dict()
    elif isinstance(lra, dict):
        d = lra
    else:
        return f"``````"

    md = []
    
    md.append(f"#### 📋 Issue\n{(d.get('issue') or '').strip()}")
    md.append("---") 
    
    md.append(f"#### 💡 Short Answer\n{(d.get('short_answer') or '').strip()}")
    md.append("---")
    
    md.append(f"#### ⚖️ Legal Rule\n{(d.get('rule') or '').strip()}")
    md.append("---")
    
    md.append(f"#### 🔍 Analysis\n{(d.get('analysis') or '').strip()}")
    md.append("---")
    
    md.append(f"#### ✅ Conclusion\n{(d.get('conclusion') or '').strip()}")
    
    cits = d.get("citations") or []
    if isinstance(cits, list) and cits:
        md.append("---")
        md.append("#### 📚 Citations")
        lines = []
        for c in cits:
            if hasattr(c, "model_dump"):
                c = c.model_dump()
            title = c.get("title") or "Source"
            cite = c.get("citation") or ""
            link = c.get("link") or ""
            juris = c.get("jurisdiction") or ""
            scc = "⭐ SCC" if c.get("SCC_citation") else ""
            meta = " • ".join([b for b in [cite, juris, scc] if b])
            label = f"[{title}]({link})" if link else title
            lines.append(f"- {label}{(' — ' + meta) if meta else ''}")
        md.append("\n".join(lines))

    meta_items = []
    if d.get("confidence_score") is not None:
        score = float(d['confidence_score'])
        emoji = "🟢" if score >= 0.8 else "🟡" if score >= 0.5 else "🔴"
        meta_items.append(f"{emoji} **Confidence:** {score:.2f}")
    if d.get("judgement"):
        meta_items.append(f"⚖️ **Status:** {d['judgement']}")
    
    if meta_items:
        md.append("---")
        md.append(" • ".join(meta_items))
    
    return "\n\n".join(md)

def format_retrieved_context(context) -> str:
    """Convert retrieved context to readable Markdown."""
    if isinstance(context, dict):
        lines = ["**Source documents:**"]
        for key, value in context.items():
            lines.append(f"- **{key}:** {value}")
        return "\n".join(lines)
    
    elif isinstance(context, list):
        lines = ["**Source documents:**"]
        for i, item in enumerate(context, 1):
            if isinstance(item, dict):
                title = item.get("title") or item.get("source") or f"Document {i}"
                content = item.get("content") or item.get("text") or str(item)
                lines.append(f"\n**{i}. {title}**\n> {content}")
            else:
                lines.append(f"\n**{i}.**\n> {str(item)}")
        return "\n".join(lines)
    
    else:
        return str(context)