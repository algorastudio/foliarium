"""Entry point: ``python -m mcp_server``.

Avvia il server MCP in stdio mode, compatibile con Claude Desktop e con
qualunque client MCP che lancia il server come sub-processo.
"""

from mcp_server.server import main


if __name__ == "__main__":
    main()
