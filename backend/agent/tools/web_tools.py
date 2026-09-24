from smolagents import Tool
from duckduckgo_search import DDGS

class WebSearchTool(Tool):
    name = "web_search"
    description = "Searches the web using DuckDuckGo."
    inputs = {
        "query": {
            "type": "string",
            "description": "The search query."
        }
    }
    output_type = "string"

    def forward(self, query: str) -> str:
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n")
            if not results:
                return "No results found."
            return "\n".join(results)
        except Exception as e:
            return f"Error searching web: {e}"
