# Fetch-Save MCP Server

A Model Context Protocol server that provides web content fetching and local file saving capabilities. This server enables LLMs to retrieve content from web pages, convert HTML to markdown for easier consumption, and save the retrieved content to a local file.

The key difference from the standard fetch MCP server is that this server provides a **fetch-save** tool that both retrieves content AND stores it locally in a permanent file, allowing for later access or processing of the data.

> [!CAUTION]
> This server can access local/internal IP addresses and may represent a security risk. Exercise caution when using this MCP server to ensure this does not expose any sensitive data.

Additional Note: The Readme and some code was written/edited with Claude Code - so parts may be incorrect. Please submit a PR if there are changes needed.

## Available Tools

- `fetch-save` - Fetches a URL from the internet, extracts its contents as markdown, and SAVES it to a local file.
    - `url` (string, required): URL to fetch and download
    - `filepath` (string, required): Local filepath where the downloaded content will be saved

## Prompts

- **fetch-save**
  - Fetch a URL and save its contents to a local file
  - Arguments:
    - `url` (string, required): URL to fetch and download
    - `filepath` (string, required): Local filepath where content will be saved

## Installation

Optionally: Install node.js, this will cause the fetch server to use a different HTML simplifier that is more robust.

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-fetch-save*.

### Using PIP

Alternatively you can install `mcp-server-fetch-save` via pip:

```
pip install mcp-server-fetch-save
```

After installation, you can run it as a script using:

```
python -m mcp_server_fetch_save
```

## Configuration

### Configure for Claude.app

Add to your Claude settings:

<details>
<summary>Using uvx</summary>

```json
"mcpServers": {
  "fetch-save": {
    "command": "uvx",
    "args": ["mcp-server-fetch-save"]
  }
}
```
</details>

<details>
<summary>Using pip installation</summary>

```json
"mcpServers": {
  "fetch-save": {
    "command": "python",
    "args": ["-m", "mcp_server_fetch_save"]
  }
}
```
</details>

### Configure for VS Code

For manual installation, add the following JSON block to your User Settings (JSON) file in VS Code. You can do this by pressing `Ctrl + Shift + P` and typing `Preferences: Open User Settings (JSON)`.

Optionally, you can add it to a file called `.vscode/mcp.json` in your workspace. This will allow you to share the configuration with others.

> Note that the `mcp` key is needed when using the `mcp.json` file.

<details>
<summary>Using uvx</summary>

```json
{
  "mcp": {
    "servers": {
      "fetch-save": {
        "command": "uvx",
        "args": ["mcp-server-fetch-save"]
      }
    }
  }
}
```
</details>

### Customization - robots.txt

By default, the server will obey a websites robots.txt file if the request came from the model (via a tool), but not if
the request was user initiated (via a prompt). This can be disabled by adding the argument `--ignore-robots-txt` to the
`args` list in the configuration.

### Customization - User-agent

By default, depending on if the request came from the model (via a tool), or was user initiated (via a prompt), the
server will use either the user-agent
```
ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)
```
or
```
ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)
```

This can be customized by adding the argument `--user-agent=YourUserAgent` to the `args` list in the configuration.

### Customization - Proxy

The server can be configured to use a proxy by using the `--proxy-url` argument.

## Debugging

You can download this repo, and add this to your `.mcp.json` file to run/test locallly.

```
{
  "mcpServers": {
    "fetch_save": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/clone/of/project/mcp-server-fetch-save/src/mcp_server_fetch_save",
        "run",
        "__main__.py"
      ]
    }
  }
}

```

You can use the MCP inspector to debug the server. For uvx installations:

```
npx @modelcontextprotocol/inspector uvx mcp-server-fetch-save
```

Or if you've installed the package in a specific directory or are developing on it:

```
cd path/to/mcp-server-fetch-save
npx @modelcontextprotocol/inspector uv run mcp-server-fetch-save
```

## Contributing

We encourage contributions to help expand and improve mcp-server-fetch-save. Whether you want to add new tools, enhance existing functionality, or improve documentation, your input is valuable.

For examples of other MCP servers and implementation patterns, see:
https://github.com/modelcontextprotocol/servers

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-fetch-save even more powerful and useful.

## License

mcp-server-fetch-save is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.

## Thanks

This server was developed based on the original [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) fetch server, with additional functionality for saving content to local files.
