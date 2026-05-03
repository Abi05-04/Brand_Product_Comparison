import asyncio
import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from fastmcp import Client

load_dotenv()

st.title("Brand Product Comparison")

st.sidebar.header("⚙️ Configuration")
st.sidebar.markdown("Enter your API key to fetch live data. You can get a free token from SerpAPI.")
ui_serp_key = st.sidebar.text_input("SerpAPI Key (SERP_API_KEY)", type="password", value=os.getenv("SERP_API_KEY", ""))

if ui_serp_key:
    os.environ["SERP_API_KEY"] = ui_serp_key

# Brand selection inputs
col1, col2, col3 = st.columns(3)
with col1:
    brand1 = st.text_input("First Brand", value="Nike", placeholder="e.g., Nike")
with col2:
    brand2 = st.text_input("Second Brand", value="Puma", placeholder="e.g., Puma")
with col3:
    product_cat = st.text_input("Product/Category (Optional)", value="", placeholder="e.g., shirts, shoes")

async def run_comparison(brand1_name, brand2_name, product_query=""):
    if not ui_serp_key:
        st.error("⚠️ Please provide the SerpAPI Key in the sidebar configuration.")
        return

    # connect to FastMCP server via stdio
    # The subprocess will inherit the OS environment variables, thus seeing SERP_API_KEY.
    async with Client("compareserver.py") as client:

        # call MCP tools to retrieve raw SerpApi datasets
        brand1_response = await client.call_tool(
            "get_brand_data",
            {"brand_name": brand1_name, "product_type": product_query}
        )

        brand2_response = await client.call_tool(
            "get_brand_data",
            {"brand_name": brand2_name, "product_type": product_query}
        )

        # Retrieve raw lists passed back from the server wrapper
        # The primary way fastmcp encodes structured data is .data
        brand1_data = getattr(brand1_response, "data", None)
        brand2_data = getattr(brand2_response, "data", None)
        
        # Fallback to json-parsing TextContent if .data is not populated
        if brand1_data is None:
            try:
                import json
                brand1_data = json.loads(brand1_response.content[0].text)
            except Exception:
                brand1_data = []
                
        if brand2_data is None:
            try:
                import json
                brand2_data = json.loads(brand2_response.content[0].text)
            except Exception:
                brand2_data = []

        # Ensure lists
        if not isinstance(brand1_data, list):
            brand1_data = [brand1_data] if brand1_data else []
        if not isinstance(brand2_data, list):
            brand2_data = [brand2_data] if brand2_data else []

        # Build list containing tagged dictionary products
        all_data = []
        for item in brand1_data:
            if isinstance(item, dict):
                item['brand'] = brand1_name
                all_data.append(item)
                
        for item in brand2_data:
            if isinstance(item, dict):
                item['brand'] = brand2_name
                all_data.append(item)

        if not all_data:
            st.warning("No tabular data returned by the search.")
            return

        # convert to pandas dataframe natively
        df = pd.DataFrame(all_data)
        st.success("✅ Results Retrieved Directly from Google Shopping!")
        st.subheader(f"{brand1_name} vs {brand2_name}")
        
        # Configure columns for better display
        st.dataframe(
            df,
            column_config={
                "link": st.column_config.LinkColumn("Product Link"),
                "price": st.column_config.TextColumn("Price"),
                "rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
                "reviews": st.column_config.NumberColumn("Reviews"),
                "store": st.column_config.TextColumn("Store"),
                "title": st.column_config.TextColumn("Product Title"),
                "brand": st.column_config.TextColumn("Brand")
            },
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.subheader("📊 Comparison Analytics")

        # Parse numeric prices for charting (stripping currency symbols and commas)
        def parse_price(val):
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                val_str = str(val).replace('₹', '').replace('$', '').replace(',', '').replace('Rs.', '').strip()
                return float(val_str)
            except Exception:
                return 0.0

        # Create a numeric dataframe copy for aggregation
        calc_df = df.copy()
        calc_df['numeric_price'] = calc_df['price'].apply(parse_price)
        calc_df['rating'] = pd.to_numeric(calc_df['rating'], errors='coerce').fillna(0)

        # Average Price Chart
        avg_price = calc_df.groupby('brand')['numeric_price'].mean().reset_index()
        avg_price = avg_price.rename(columns={'numeric_price': 'Average Price (₹)', 'brand': 'Brand'})

        # Average Rating Chart
        avg_rating = calc_df.groupby('brand')['rating'].mean().reset_index()
        avg_rating = avg_rating.rename(columns={'rating': 'Average Rating', 'brand': 'Brand'})

        graph_col1, graph_col2 = st.columns(2)
        with graph_col1:
            st.markdown("**Average Price by Brand**")
            st.bar_chart(avg_price, x='Brand', y='Average Price (₹)', use_container_width=True)
            
        with graph_col2:
            st.markdown("**Average Rating by Brand**")
            st.bar_chart(avg_rating, x='Brand', y='Average Rating', use_container_width=True)

click = st.button("Run Brand Comparison")
if click:
    with st.spinner("🔄 Fetching live data..."):
        try:
            asyncio.run(run_comparison(brand1, brand2, product_cat))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_comparison(brand1, brand2, product_cat))
        except Exception as e:
            st.error(f"❌ Hard Error: {type(e).__name__}: {str(e)}")
            st.text(str(e))