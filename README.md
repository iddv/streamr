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

## 📊 Current Status

**Project Phase**: Phase 1 - Product Definition & Strategy (Extended)  
**Progress**: 25% Complete - Foundation & AI System Operational  
**Status**: 🟢 On Track

👉 **[View Detailed Status & Next Steps](CURRENT_STATUS.md)**

### Recent Achievements
- ✅ Technical feasibility validated with 3 innovation opportunities
- ✅ AI advisor consultation system operational
- ✅ Comprehensive research documentation completed
- 🔄 Market analysis in progress using AI advisors

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/iddv/streamr-ai-advisors-mcp.git
cd streamr-ai-advisors-mcp

# Install dependencies
pip install fastmcp

# Or with poetry
poetry install
```

### Running the Server

```bash
# Development mode (stdio transport)
python streamr_advisors_server.py

# HTTP server mode
python streamr_advisors_server.py --transport http --port 8000

# Custom output directory
python streamr_advisors_server.py --output-dir ./my_consultations
```

## 🛠️ Available Tools

### Core Consultation Tools

- `ask_infrastructure_visionary(question, save_to_file=True)` - Technical architecture consultation
- `ask_economic_architect(question, save_to_file=True)` - Tokenomics and economic justice consultation  
- `ask_community_catalyst(question, save_to_file=True)` - Community building and partnership consultation

### Utility Tools

- `get_advisor_info()` - Get information about all available advisors
- `set_output_directory(directory_path)` - Configure where responses are saved

### Resources

- `advisor://personas` - Detailed information about all AI personas
- `advisor://outputs` - List of recent consultation outputs

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
      "command": "python",
      "args": ["/path/to/streamr_advisors_server.py"],
      "env": {
        "STREAMR_OUTPUT_DIR": "/path/to/your/consultations"
      }
    }
  }
}
```

## 🧪 Development

### Testing the Server

```bash
# Test with MCP inspector
mcp dev streamr_advisors_server.py

# Test HTTP mode
python streamr_advisors_server.py --transport http --port 8000
curl http://localhost:8000/tools
```

### Code Quality

```bash
# Format code
black .
isort .

# Lint
ruff check .

# Type checking
mypy .
```

## 🏗️ Architecture

The server is built using [FastMCP](https://github.com/jlowin/fastmcp) and provides:

- **Tools**: Direct consultation functions for each AI persona
- **Resources**: Access to persona definitions and consultation history
- **File Output**: Automatic saving of responses to markdown files
- **Flexible Transport**: Support for both stdio and HTTP protocols

## 🔮 Future Enhancements

- **LLM Integration**: Connect to actual LLM APIs (Claude, OpenAI) for dynamic responses
- **Conversation Memory**: Track consultation history and context
- **Multi-Agent Collaboration**: Tools for consulting multiple personas on complex decisions
- **Response Templates**: Customizable output formats for different use cases

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📚 Documentation Index

### Project Management
- **[Current Status & Next Steps](CURRENT_STATUS.md)** - Comprehensive status overview and immediate action items
- **[Project Tracker](research/project_tracker.md)** - Detailed phase tracking and milestone management
- **[AI Agent Usage Guide](research/ai_agent_usage_guide.md)** - How to use the AI advisor consultation system

### Product Research
- **[PRFAQ](research/prfaq.md)** - Product vision and frequently asked questions
- **[Feasibility Analysis](research/compass_artifact_wf-023ffc89-1689-4915-9001-b456dd0430c8_text_markdown.md)** - Technical validation and innovation opportunities
- **[Product Development Plan](research/product_development_plan.md)** - Comprehensive development strategy

### AI Advisor Personas
- **[Decentralized Infrastructure Visionary](research/decentralized_infrastructure_visionary_job_spec.md)** - CTO perspective
- **[Economic Justice Architect](research/economic_justice_architect_job_spec.md)** - Tokenomics perspective  
- **[Human Connection Catalyst](research/human_connection_catalyst_job_spec.md)** - Community perspective

### Technical Implementation
- **[MCP Server Documentation](mcp-server/README.md)** - AI advisor server setup and usage
- **[MCP Server Code](mcp-server/streamr_advisors_server.py)** - FastMCP implementation

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) by Jeremiah Lowin
- Inspired by the [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- Part of the StreamrP2P project ecosystem

---

**🚀 Ready to consult with your AI advisors? Start the server and begin building the future of decentralized streaming!** 