from .server import serve


def main():
    """MCP Fetch Save Server - Download web content and save to local files"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="MCP server for downloading web content and saving it permanently to local files"
    )
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent string")
    parser.add_argument(
        "--ignore-robots-txt",
        action="store_true",
        help="Ignore robots.txt restrictions",
    )
    parser.add_argument("--proxy-url", type=str, help="Proxy URL to use for requests")

    args = parser.parse_args()
    asyncio.run(serve(args.user_agent, args.ignore_robots_txt, args.proxy_url))


if __name__ == "__main__":
    main()
