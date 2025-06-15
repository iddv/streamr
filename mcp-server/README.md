# StreamrP2P AI Advisors MCP Server

🤖 **AI-powered consultation system for StreamrP2P product development**

This MCP server provides access to three specialized AI agent personas that can offer expert consultation on different aspects of the StreamrP2P blockchain-integrated mobile P2P streaming platform.

## 🎯 Available AI Advisors

### 🔧 Decentralized Infrastructure Visionary
- **Role**: CTO with deep P2P/blockchain expertise
- **Expertise**: Technical architecture, P2P networking, blockchain integration, mobile optimization
- **Use For**: Technical architecture decisions, infrastructure trade-offs, optimization strategies

### 💰 Economic Justice Architect
- **Role**: Economic justice advocate with tokenomics expertise  
- **Expertise**: Token economics, revenue sharing, user earning optimization, anti-exploitation economics
- **Use For**: Tokenomics design, revenue models, creator economy policies, economic justice analysis

### 🌍 Human Connection Catalyst
- **Role**: Community organizer with social entrepreneurship skills
- **Expertise**: Community building, cultural adaptation, partnership development, user education
- **Use For**: Community strategy, partnership decisions, cultural adaptation, user onboarding

## 🚀 Quick Start

### Installation

```bash
# Install FastMCP
pip install fastmcp

# Or install all dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Development mode (stdio transport)
python3 streamr_advisors_server.py

# HTTP server mode
python3 streamr_advisors_server.py --transport http --port 8000

# Custom output directory
python3 streamr_advisors_server.py --output-dir ../consultations
```

## 🛠️ Available Tools

### Core Consultation Tools

- `ask_infrastructure_visionary(question, save_to_file=True)` - Technical architecture consultation
- `ask_economic_architect(question, save_to_file=True)` - Tokenomics and economic justice consultation  
- `ask_community_catalyst(question, save_to_file=True)` - Community building and partnership consultation
- `ask_all_advisors(question, save_to_file=True)` - Get all three perspectives on complex decisions

### Utility Tools

- `get_advisor_info()` - Get information about all available advisors
- `set_output_directory(directory_path)` - Configure where responses are saved

### Resources

- `advisor://personas` - Detailed information about all AI personas
- `advisor://outputs` - List of recent consultation outputs
- `advisor://research` - StreamrP2P project context from research folder

## 📝 Usage Examples

### Technical Architecture Question
```python
# Ask about P2P streaming protocols
result = ask_infrastructure_visionary(
    "Should we use WebRTC or custom UDP protocols for mobile P2P streaming?"
)
```

### Tokenomics Question
```python
# Ask about reward structures
result = ask_economic_architect(
    "How should we structure viewer rewards to ensure sustainable earning without creating exploitation?"
)
```

### Community Strategy Question
```python
# Ask about international expansion
result = ask_community_catalyst(
    "How should we approach international expansion while respecting local communities?"
)
```

### Multi-Perspective Analysis
```python
# Get all three perspectives on a complex decision
result = ask_all_advisors(
    "Should we implement a micro-payment system for premium content?"
)
```

## 📁 Output Management

All consultation responses are automatically saved as markdown files in the configured output directory (default: `./advisor_outputs`).

File naming pattern: `{persona_key}_{timestamp}.md`

Example files:
- `infrastructure_visionary_20241201_143022.md`
- `economic_architect_20241201_143045.md`
- `community_catalyst_20241201_143108.md`

## 🔧 Configuration

### Environment Variables

- `STREAMR_OUTPUT_DIR` - Default output directory for consultation responses

### Command Line Options

- `--transport` - Transport protocol (`stdio` or `http`)
- `--host` - Host for HTTP transport (default: `localhost`)
- `--port` - Port for HTTP transport (default: `8000`)
- `--output-dir` - Directory for saving responses (default: `./advisor_outputs`)

## 🎮 Claude Desktop Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "streamr-advisors": {
      "command": "python3",
      "args": ["/path/to/streamr/mcp-server/streamr_advisors_server.py"],
      "env": {
        "STREAMR_OUTPUT_DIR": "/path/to/your/consultations"
      }
    }
  }
}
```

## 🧪 Development & Testing

### Testing the Server

```bash
# Test with MCP inspector (if available)
mcp dev streamr_advisors_server.py

# Test HTTP mode
python3 streamr_advisors_server.py --transport http --port 8000
curl http://localhost:8000/tools
```

### Integration with Research

This MCP server is designed to work with the StreamrP2P research documentation in the `../research/` folder:

- **Persona Guidelines**: Full AI agent specifications in `*_job_spec.md` files
- **Project Context**: PRFAQ, project tracker, and feasibility analysis
- **Usage Guide**: Complete instructions in `ai_agent_usage_guide.md`

## 🔮 Production Integration

**Current Status**: This is a template implementation that returns structured template responses.

**For Production Use**:

1. **Integrate with LLM APIs**:
   ```python
   # Replace generate_ai_response() with actual LLM calls
   import openai  # or anthropic for Claude
   
   def generate_ai_response(persona_key: str, question: str) -> str:
       persona = PERSONAS[persona_key]
       response = openai.ChatCompletion.create(
           model="gpt-4",
           messages=[
               {"role": "system", "content": persona["persona_prompt"]},
               {"role": "user", "content": question}
           ]
       )
       return response.choices[0].message.content
   ```

2. **Load Full Persona Guidelines**:
   ```python
   # Load complete persona specifications from research folder
   def load_persona_from_research(persona_key: str) -> str:
       with open(f"../research/{persona_key}_job_spec.md", "r") as f:
           return f.read()
   ```

3. **Add Conversation Memory**:
   - Track consultation history
   - Maintain context across questions
   - Reference previous decisions

## 🏗️ Architecture

The server is built using [FastMCP](https://github.com/jlowin/fastmcp) and provides:

- **Tools**: Direct consultation functions for each AI persona
- **Resources**: Access to persona definitions, consultation history, and research context
- **File Output**: Automatic saving of responses to markdown files
- **Flexible Transport**: Support for both stdio and HTTP protocols

## 📄 License

MIT License - Part of the StreamrP2P project ecosystem.

## 🤝 Contributing

This MCP server is part of the larger StreamrP2P project. See the main project README and research documentation for contribution guidelines.

---

**🚀 Ready to consult with your AI advisors? Start the server and begin building the future of decentralized streaming!** 