# uv: requirements = ["urllib", "markdownify", "readabilipy", "mcp", "protego", "pydantic"]

from typing import Annotated, Tuple
from urllib.parse import urlparse, urlunparse
import os

import markdownify
import readabilipy.simple_json
from mcp.shared.exceptions import McpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ErrorData,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from protego import Protego
from pydantic import BaseModel, Field, AnyUrl, FilePath

DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"


def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content
    """
    ret = readabilipy.simple_json.simple_json_from_html_string(
        html, use_readability=True
    )
    if not ret["content"]:
        return "<error>Page failed to be simplified from HTML</error>"
    content = markdownify.markdownify(
        ret["content"],
        heading_style=markdownify.ATX,
    )
    return content


def save_content_to_file(content: str, filepath: str) -> None:
    """Save content to a file.

    Args:
        content: Content to save
        filepath: Path to the file where content should be saved

    Raises:
        OSError: If there is an error saving to the file
    """
    # Create directory if it doesn't exist
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # Write content to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def get_robots_txt_url(url: str) -> str:
    """Get the robots.txt URL for a given website URL.

    Args:
        url: Website URL to get robots.txt for

    Returns:
        URL of the robots.txt file
    """
    # Parse the URL into components
    parsed = urlparse(url)

    # Reconstruct the base URL with just scheme, netloc, and /robots.txt path
    robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))

    return robots_url


async def check_may_autonomously_fetch_url(url: str, user_agent: str, proxy_url: str | None = None) -> None:
    """
    Check if the URL can be fetched by the user agent according to the robots.txt file.
    Raises a McpError if not.
    """
    from httpx import AsyncClient, HTTPError

    robot_txt_url = get_robots_txt_url(url)

    async with AsyncClient(proxies=proxy_url) as client:
        try:
            response = await client.get(
                robot_txt_url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
            )
        except HTTPError:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to fetch robots.txt {robot_txt_url} due to a connection issue",
            ))
        if response.status_code in (401, 403):
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"When fetching robots.txt ({robot_txt_url}), received status {response.status_code} so assuming that autonomous fetching is not allowed, the user can try manually fetching by using the fetch prompt",
            ))
        elif 400 <= response.status_code < 500:
            return
        robot_txt = response.text
    processed_robot_txt = "\n".join(
        line for line in robot_txt.splitlines() if not line.strip().startswith("#")
    )
    robot_parser = Protego.parse(processed_robot_txt)
    if not robot_parser.can_fetch(str(url), user_agent):
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"The sites robots.txt ({robot_txt_url}), specifies that autonomous fetching of this page is not allowed, "
            f"<useragent>{user_agent}</useragent>\n"
            f"<url>{url}</url>"
            f"<robots>\n{robot_txt}\n</robots>\n"
            f"The assistant must let the user know that it failed to view the page. The assistant may provide further guidance based on the above information.\n"
            f"The assistant can tell the user that they can try manually fetching the page by using the fetch prompt within their UI.",
        ))


async def fetch_url(
    url: str, user_agent: str, force_raw: bool = False, proxy_url: str | None = None
) -> Tuple[str, str, str]:
    """
    Fetch the URL and return the content in a form ready for the LLM, a prefix string with status information, and the content type.
    """
    from httpx import AsyncClient, HTTPError

    async with AsyncClient(proxies=proxy_url) as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=30,
            )
        except HTTPError as e:
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"))
        if response.status_code >= 400:
            raise McpError(ErrorData(
                code=INTERNAL_ERROR,
                message=f"Failed to fetch {url} - status code {response.status_code}",
            ))

        page_raw = response.text

    content_type = response.headers.get("content-type", "")
    is_page_html = (
        "<html" in page_raw[:100] or "text/html" in content_type or not content_type
    )

    if is_page_html and not force_raw:
        return extract_content_from_html(page_raw), "", content_type

    return (
        page_raw,
        f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
        content_type
    )


class Fetch(BaseModel):
    """Parameters for fetching a URL and saving the content to a local file for storage and future use."""

    url: Annotated[AnyUrl, Field(description="URL to fetch and download for local storage")]
    filepath: Annotated[FilePath, Field(description="Local filepath where the downloaded content will be saved")]
    

async def serve(
    custom_user_agent: str | None = None,
    ignore_robots_txt: bool = False,
    proxy_url: str | None = None,
) -> None:
    """Run the fetch-save MCP server.

    Args:
        custom_user_agent: Optional custom User-Agent string to use for requests
        ignore_robots_txt: Whether to ignore robots.txt restrictions
        proxy_url: Optional proxy URL to use for requests
    """
    server = Server("mcp-fetch-save")
    user_agent_autonomous = custom_user_agent or DEFAULT_USER_AGENT_AUTONOMOUS
    user_agent_manual = custom_user_agent or DEFAULT_USER_AGENT_MANUAL

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="fetch-save",
                description="""Fetches a URL from the internet and SAVES the contents to a LOCAL FILE. This tool is specifically designed for DOWNLOADING and STORING web content to your filesystem.

When you need to both access online content AND save it locally for later use or processing, THIS is the appropriate tool to use. Unlike the regular fetch tool which only displays content, this tool permanently stores the fetched data in a file.

Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.""",
                inputSchema=Fetch.model_json_schema(),
            )
        ]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="fetch-save",
                description="DOWNLOAD and SAVE web content to a local file (use this when you need to store fetched content)",
                arguments=[
                    PromptArgument(
                        name="url", description="URL to fetch and download", required=True
                    ),
                    PromptArgument(
                        name="filepath", description="Local file path where content will be saved", required=True
                    )
                ],
            )
        ]

    @server.call_tool()
    async def call_tool(name, arguments: dict) -> list[TextContent]:
        try:
            args = Fetch(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        url = str(args.url)
        filepath = str(args.filepath)

        if not url:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

        if not filepath:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Filepath is required"))

        if not ignore_robots_txt:
            await check_may_autonomously_fetch_url(url, user_agent_autonomous, proxy_url)

        content, prefix, content_type = await fetch_url(
            url, user_agent_autonomous, force_raw=False, proxy_url=proxy_url
        )
        original_length = len(content)

        save_content_to_file(content, filepath)
        
        return [TextContent(type="text", text=f"{prefix}Successfully DOWNLOADED and SAVED content from {url} to {filepath}. The file has been created for permanent storage. Content length: {len(content)} characters.\n")]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        if not arguments or "url" not in arguments or "filepath" not in arguments:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL and filepath are required"))

        url = arguments["url"]
        filepath = arguments["filepath"]

        try:
            content, prefix, content_type = await fetch_url(url, user_agent_manual, proxy_url=proxy_url)

            # Save content to the specified filepath
            try:
                save_content_to_file(content, filepath)
                save_message = f"\nContent successfully saved to: {filepath}"
            except OSError as file_error:
                save_message = f"\nError saving content to file: {str(file_error)}"

            # TODO: after SDK bug is addressed, don't catch the exception
        except McpError as e:
            return GetPromptResult(
                description=f"Failed to fetch {url}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=str(e)),
                    )
                ],
            )
        return GetPromptResult(
            description=f"Fetched content from {url}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Successfully fetched content from {url}. {save_message}\n\nContent type: {content_type}\nContent length: {len(content)} characters"
                    )
                )
            ],
        )

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
