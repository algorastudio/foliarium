"""mcp_server — Foliarium MCP server per Claude Desktop e altri client MCP.

Espone la REST API di Foliarium (vedi ``api/``) come tool invocabili da
Claude attraverso il Model Context Protocol (https://modelcontextprotocol.io).

Configurazione via env var:

* ``FOLIARIUM_API_BASE_URL`` — URL base dell'API (es. ``http://localhost:8765``)
* ``FOLIARIUM_API_KEY``      — chiave API (formato ``flr_<32 hex>``), generata
  dal dialog *Impostazioni → Gestione Chiavi API…* dell'app desktop.

Esecuzione (Claude Desktop o compatibili):

.. code-block:: json

    {
      "mcpServers": {
        "foliarium": {
          "command": "python",
          "args": ["-m", "mcp_server"],
          "env": {
            "FOLIARIUM_API_BASE_URL": "http://localhost:8765",
            "FOLIARIUM_API_KEY": "flr_xxxxxxxx..."
          }
        }
      }
    }
"""

from mcp_server.server import build_server, main  # noqa: F401

__all__ = ["build_server", "main"]
