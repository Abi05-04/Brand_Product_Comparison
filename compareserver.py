import streamlit as st
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from serpapi import GoogleSearch

load_dotenv()
serp = os.getenv("SERP_API_KEY")

mcp = FastMCP("Brand Comparison Server")

@mcp.tool()
def get_brand_data(brand_name: str, product_type: str = "") -> list:
    """
    Fetches real-time shopping data for a specific brand and product type.
    """
    if not serp:
        return [{"title": "Error: SERP_API_KEY not found", "price": 0, "rating": 0}]

    query = f"{brand_name} {product_type}".strip()
    
    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": serp,
        "num": 3,
        "gl": "in",
        "hl": "en",
        "google_domain": "google.co.in"
    }
    search = GoogleSearch(params)
    data = search.get_dict()
    
    if "error" in data:
        return [{"title": f"SerpAPI Error: {data['error']}", "price": "N/A", "rating": "N/A"}]
        
    results = data.get("shopping_results", [])
    if not results:
        return [{"title": "No shopping results found.", "price": "N/A", "rating": "N/A", "store": "N/A"}]
    
    products = []
    for r in results:
        # Better price parsing
        price = r.get("price")
        if not price:
            price = r.get("extracted_price")
        if not price and r.get("prices"):
            price = r.get("prices")[0].get("price", "Unknown")
            
        products.append({
            "title": r.get("title", "Unknown"), 
            "price": price, 
            "rating": r.get("rating", "N/A"),
            "reviews": r.get("reviews", "0"),
            "store": r.get("source", "Unknown Store"),
            "link": r.get("link", "")
        })
        
    return products

if __name__ == "__main__":
    mcp.run()