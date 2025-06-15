#!/usr/bin/env python3
"""
StreamrP2P AI Advisors MCP Server

Provides access to three AI agent personas as tools for StreamrP2P consultation:
- Decentralized Infrastructure Visionary (CTO perspective)
- Economic Justice Architect (Tokenomics perspective) 
- Human Connection Catalyst (Community perspective)

Each persona can be consulted via tools and outputs responses to markdown files.
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from fastmcp import FastMCP
except ImportError:
    print("FastMCP not found. Installing...")
    os.system("pip install fastmcp")
    from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("StreamrP2P AI Advisors")

# Configuration
OUTPUT_DIR = os.getenv("STREAMR_OUTPUT_DIR", "./advisor_outputs")
Path(OUTPUT_DIR).mkdir(exist_ok=True)

# AI Agent Personas
PERSONAS = {
    "infrastructure_visionary": {
        "name": "Decentralized Infrastructure Visionary",
        "role": "CTO with deep P2P/blockchain expertise",
        "expertise": "Technical architecture, P2P networking, blockchain integration, mobile optimization",
        "decision_lens": "Performance-driven, decentralization-first, mobile battery optimization, scalability",
        "persona_prompt": """You are the Decentralized Infrastructure Visionary for StreamrP2P. You embody a seasoned CTO with deep expertise in P2P networks, blockchain infrastructure, and mobile-first architecture. 

Your thinking framework:
- Systems thinking: You naturally think in architectural layers and component interactions
- Performance optimization: Every decision evaluated through latency, throughput, and resource efficiency
- Decentralization principles: Prefer distributed solutions over centralized ones
- Mobile-first constraints: Always consider battery life, network variability, and device limitations

Your communication style:
- Technical precision: Use specific metrics and benchmarks
- Architecture focus: Frame solutions in terms of system design and scalability
- Trade-off analysis: Always present multiple options with clear pros/cons
- Implementation clarity: Provide concrete technical recommendations

Key StreamrP2P context:
- Target: Sub-5-second mobile latency for P2P streaming
- Goal: 80% infrastructure cost reduction through P2P
- Challenge: Mobile battery optimization while maintaining performance
- Innovation: Hybrid P2P-CDN architecture with blockchain coordination"""
    },
    
    "economic_architect": {
        "name": "Economic Justice Architect", 
        "role": "Economic justice advocate with tokenomics expertise",
        "expertise": "Token economics, revenue sharing, user earning optimization, anti-exploitation economics",
        "decision_lens": "Creator empowerment, user earning maximization, wealth redistribution, transparency",
        "persona_prompt": """You are the Economic Justice Architect for StreamrP2P. You combine the passion of an economic justice advocate with the analytical rigor of a tokenomics expert. You see technology as a tool for wealth redistribution.

Your thinking framework:
- Justice-first economics: Every decision evaluated through "does this increase economic opportunity for the 99%?"
- Anti-exploitation analysis: Constantly vigilant against systems that extract value from users
- Transparency imperative: All economic mechanisms must be clearly understandable
- Sustainable earning focus: Long-term user earning potential over short-term platform profits

Your communication style:
- Values-driven: Frame economic arguments in terms of fairness and justice
- Data-backed advocacy: Use concrete numbers to support justice arguments
- User empowerment focus: Always consider how decisions affect user earning potential
- Systemic analysis: Connect individual features to broader economic patterns

Key StreamrP2P context:
- Goal: 90% creator revenue share (vs 50% industry standard)
- Target: $50-200 monthly viewer earnings through watch-to-earn
- Innovation: Gaming hardware monetization for idle GPU/CPU utilization
- Principle: Users should earn more than they spend on the platform"""
    },
    
    "community_catalyst": {
        "name": "Human Connection Catalyst",
        "role": "Community organizer with social entrepreneurship skills", 
        "expertise": "Community building, cultural adaptation, partnership development, user education",
        "decision_lens": "People-first approach, community empowerment, cultural humility, relationship building",
        "persona_prompt": """You are the Human Connection Catalyst for StreamrP2P. You combine the heart of a community organizer with the skills of a social entrepreneur. You see technology as a tool for human connection and community empowerment.

Your thinking framework:
- People-first approach: Technology serves human relationships, not the other way around
- Community asset focus: You naturally identify and amplify existing community strengths
- Collective empowerment: Solutions should increase community capacity for self-determination
- Multi-stakeholder perspective: Consider impacts on creators, viewers, communities, and broader society

Your communication style:
- Inclusive language: Use "we" and "us" naturally, avoiding insider technical jargon
- Story-driven: Frame concepts through human stories and community examples
- Empathetic inquiry: Ask questions that reveal people's real needs and motivations
- Bridge-building: Translate between different community perspectives and find common ground

Key StreamrP2P context:
- Goal: Build engaged communities across gaming, streaming, and crypto audiences
- Challenge: Onboarding mainstream users to cryptocurrency and P2P concepts
- Innovation: Community-owned infrastructure with local P2P nodes
- Principle: Communities should have genuine participation in platform governance"""
    }
}

def generate_ai_response(persona_key: str, question: str) -> str:
    """
    Generate AI response for a given persona and question.
    In a real implementation, this would call an LLM API.
    For now, it returns a structured template response.
    """
    persona = PERSONAS[persona_key]
    
    # This is a simplified template response
    # In production, you'd integrate with Claude API, OpenAI, etc.
    response = f"""# {persona['name']} Response

## Question
{question}

## Analysis from {persona['role']} Perspective

*[This is a template response. In production, this would be generated by an LLM using the persona prompt and question.]*

### Key Considerations
- **Expertise Area**: {persona['expertise']}
- **Decision Lens**: {persona['decision_lens']}

### Recommended Approach
Based on my {persona['role']} perspective, I recommend:

1. **Primary Strategy**: [Specific recommendation aligned with persona's decision lens]
2. **Implementation Considerations**: [Technical/economic/community factors to consider]
3. **Success Metrics**: [How to measure success from this persona's perspective]
4. **Potential Risks**: [Concerns or challenges from this domain]

### Next Steps
- [Specific actionable next steps]
- [Stakeholder consultation recommendations]
- [Follow-up questions to explore]

---
*Generated by {persona['name']} AI Agent*
*Timestamp: {datetime.now().isoformat()}*
"""
    return response

def save_response(persona_key: str, question: str, response: str) -> str:
    """Save response to markdown file and return file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{persona_key}_{timestamp}.md"
    filepath = Path(OUTPUT_DIR) / filename
    
    with open(filepath, 'w') as f:
        f.write(response)
    
    return str(filepath)

@mcp.tool()
def ask_infrastructure_visionary(question: str, save_to_file: bool = True) -> dict:
    """
    Consult the Decentralized Infrastructure Visionary (CTO perspective) on technical architecture,
    P2P networking, blockchain integration, and mobile optimization questions.
    
    Args:
        question: Your technical question or scenario for consultation
        save_to_file: Whether to save the response to a markdown file (default: True)
    
    Returns:
        Dict with response text and optional file path
    """
    response = generate_ai_response("infrastructure_visionary", question)
    
    result = {
        "persona": "Decentralized Infrastructure Visionary",
        "response": response,
        "timestamp": datetime.now().isoformat()
    }
    
    if save_to_file:
        filepath = save_response("infrastructure_visionary", question, response)
        result["saved_to"] = filepath
    
    return result

@mcp.tool()
def ask_economic_architect(question: str, save_to_file: bool = True) -> dict:
    """
    Consult the Economic Justice Architect on tokenomics, revenue sharing, 
    user earning optimization, and economic justice questions.
    
    Args:
        question: Your economic/tokenomics question or scenario for consultation
        save_to_file: Whether to save the response to a markdown file (default: True)
    
    Returns:
        Dict with response text and optional file path
    """
    response = generate_ai_response("economic_architect", question)
    
    result = {
        "persona": "Economic Justice Architect",
        "response": response,
        "timestamp": datetime.now().isoformat()
    }
    
    if save_to_file:
        filepath = save_response("economic_architect", question, response)
        result["saved_to"] = filepath
    
    return result

@mcp.tool()
def ask_community_catalyst(question: str, save_to_file: bool = True) -> dict:
    """
    Consult the Human Connection Catalyst on community building, cultural adaptation,
    partnership development, and user education questions.
    
    Args:
        question: Your community/partnership question or scenario for consultation
        save_to_file: Whether to save the response to a markdown file (default: True)
    
    Returns:
        Dict with response text and optional file path
    """
    response = generate_ai_response("community_catalyst", question)
    
    result = {
        "persona": "Human Connection Catalyst", 
        "response": response,
        "timestamp": datetime.now().isoformat()
    }
    
    if save_to_file:
        filepath = save_response("community_catalyst", question, response)
        result["saved_to"] = filepath
    
    return result

@mcp.tool()
def get_advisor_info() -> dict:
    """Get information about all available AI advisor personas."""
    return {
        "available_advisors": [
            {
                "key": key,
                "name": persona["name"],
                "role": persona["role"],
                "expertise": persona["expertise"],
                "decision_lens": persona["decision_lens"]
            }
            for key, persona in PERSONAS.items()
        ],
        "output_directory": OUTPUT_DIR,
        "usage": {
            "infrastructure_questions": "Use ask_infrastructure_visionary() for technical architecture, P2P, blockchain questions",
            "economic_questions": "Use ask_economic_architect() for tokenomics, revenue sharing, economic justice questions", 
            "community_questions": "Use ask_community_catalyst() for community building, partnerships, cultural adaptation questions"
        }
    }

@mcp.tool()
def set_output_directory(directory_path: str) -> dict:
    """
    Set the output directory for saving advisor responses.
    
    Args:
        directory_path: Path to directory where responses should be saved
        
    Returns:
        Confirmation of directory change
    """
    global OUTPUT_DIR
    
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR = directory_path
        return {
            "success": True,
            "message": f"Output directory set to: {directory_path}",
            "directory": OUTPUT_DIR
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "current_directory": OUTPUT_DIR
        }

@mcp.resource("advisor://personas")
def get_personas_resource() -> str:
    """Resource containing detailed information about all AI advisor personas."""
    return json.dumps(PERSONAS, indent=2)

@mcp.resource("advisor://outputs")
def get_outputs_resource() -> str:
    """Resource listing recent advisor consultation outputs."""
    try:
        output_files = list(Path(OUTPUT_DIR).glob("*.md"))
        output_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        recent_outputs = []
        for file in output_files[:10]:  # Last 10 files
            stat = file.stat()
            recent_outputs.append({
                "filename": file.name,
                "path": str(file),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
        
        return json.dumps({
            "output_directory": OUTPUT_DIR,
            "recent_consultations": recent_outputs,
            "total_files": len(output_files)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StreamrP2P AI Advisors MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport protocol (default: stdio)")
    parser.add_argument("--host", default="localhost", help="Host for HTTP transport")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transport")
    parser.add_argument("--output-dir", default="./advisor_outputs", 
                       help="Directory for saving advisor responses")
    
    args = parser.parse_args()
    
    # Set output directory from command line
    OUTPUT_DIR = args.output_dir
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    print(f"🤖 StreamrP2P AI Advisors MCP Server")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"🚀 Starting server with {args.transport} transport...")
    
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run() 