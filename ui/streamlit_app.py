import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="Support Ticket AI System",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)

def check_api_health():
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None

def query_api(question: str):
    try:
        resp = requests.post(
            f"{API_BASE}/api/query",
            json={"question": question},
            timeout=60,
        )
        return resp.json(), resp.status_code
    except requests.Timeout:
        return {"error": "Request timed out"}, 504
    except Exception as e:
        return {"error": str(e)}, 500

def get_anomalies(anomaly_type=None, severity=None, limit=50):
    try:
        params = {"limit": limit}
        if anomaly_type:
            params["anomaly_type"] = anomaly_type
        if severity:
            params["severity"] = severity
        resp = requests.get(f"{API_BASE}/api/anomalies", params=params, timeout=30)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 500

def get_stats():
    try:
        resp = requests.get(f"{API_BASE}/health/data", timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None

def main():
    st.title("🎫 Support Ticket AI System")
    st.caption("Natural language queries & anomaly detection for customer support tickets")

    health = check_api_health()
    
    with st.sidebar:
        st.header("System Status")
        if health:
            status = health.get("status", "unknown")
            if status == "healthy":
                st.success(f"✅ {status.title()}")
            else:
                st.warning(f"⚠️ {status.title()}")
            
            data_status = health.get("data", {}).get("status", "unknown")
            st.write(f"Data: {data_status}")
            
            llm_info = health.get("llm", {})
            st.write(f"LLM: {llm_info.get('provider', 'unknown')} - {llm_info.get('model', 'unknown')}")
            st.write(f"Available: {'✅' if llm_info.get('available') else '❌'}")
        else:
            st.error("❌ API unreachable")
            st.info(f"Make sure API is running at {API_BASE}")

        st.divider()
        st.header("Quick Stats")
        stats = get_stats()
        if stats and "total_tickets" in stats:
            st.metric("Total Tickets", stats["total_tickets"])
            st.metric("Avg Resolution (hrs)", f"{stats.get('avg_resolution_time_hrs', 0):.1f}")
            st.metric("Avg Rating", f"{stats.get('avg_customer_rating', 0):.2f}")

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Query", "🚨 Anomalies", "📊 Statistics", "📝 Examples"])

    with tab1:
        st.header("Natural Language Query")
        
        question = st.text_input(
            "Ask a question about the tickets:",
            placeholder="e.g., How many critical tickets are unresolved?",
            key="query_input",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔍 Ask", type="primary", disabled=not question.strip()):
                with st.spinner("Processing..."):
                    result, status = query_api(question)
                
                if status == 200:
                    st.session_state.last_result = result
                else:
                    st.error(f"Error: {result.get('detail', result.get('error', 'Unknown error'))}")

        if "last_result" in st.session_state:
            result = st.session_state.last_result
            
            st.success(result.get("answer", "Done"))
            
            with st.expander("📋 Interpreted Query", expanded=False):
                st.json(result.get("interpreted_query", {}))
            
            with st.expander("📊 Data", expanded=True):
                data = result.get("data", {})
                if isinstance(data, list) and data:
                    df = pd.DataFrame(data)
                    if "created_at" in df.columns:
                        df["created_at"] = pd.to_datetime(df["created_at"])
                    st.dataframe(df, use_container_width=True)
                elif isinstance(data, dict) and data:
                    st.json(data)
                else:
                    st.info("No data returned")
            
            st.caption(f"Execution time: {result.get('execution_time_ms', 0):.1f} ms")

    with tab2:
        st.header("Anomaly Detection")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            anomaly_type_filter = st.selectbox(
                "Filter by type",
                ["All", "long_resolution_time", "unresolved_high_priority", "low_customer_rating", "long_response_time"],
                key="anomaly_type_filter",
            )
        with col2:
            severity_filter = st.selectbox(
                "Filter by severity",
                ["All", "critical", "high", "medium", "low"],
                key="severity_filter",
            )
        with col3:
            limit = st.number_input("Limit", min_value=1, max_value=500, value=50, key="anomaly_limit")

        if st.button("🔄 Refresh Anomalies", type="primary"):
            with st.spinner("Detecting anomalies..."):
                at = None if anomaly_type_filter == "All" else anomaly_type_filter
                sev = None if severity_filter == "All" else severity_filter
                result, status = get_anomalies(at, sev, limit)
            
            if status == 200:
                st.session_state.anomalies_result = result
            else:
                st.error(f"Error: {result.get('detail', result.get('error', 'Unknown error'))}")

        if "anomalies_result" in st.session_state:
            result = st.session_state.anomalies_result
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", result.get("total", 0))
            with col2:
                st.metric("Filtered", result.get("filtered", 0))
            with col3:
                st.metric("Types", len(result.get("by_type", {})))
            with col4:
                st.metric("Severities", len(result.get("by_severity", {})))

            anomalies = result.get("anomalies", [])
            if anomalies:
                df = pd.DataFrame(anomalies)
                display_cols = ["ticket_id", "anomaly_type", "severity", "metric", "value", "threshold", "reason"]
                available_cols = [c for c in display_cols if c in df.columns]
                st.dataframe(df[available_cols], use_container_width=True)
                
                with st.expander("📋 Full Details"):
                    for a in anomalies:
                        st.json(a)
            else:
                st.info("No anomalies found with current filters")

    with tab3:
        st.header("Dataset Statistics")
        
        if stats and "total_tickets" in stats:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tickets", stats["total_tickets"])
                st.metric("Missing Resolution Time", stats.get("missing_resolution_time", 0))
            with col2:
                st.metric("Avg Response Time (hrs)", f"{stats.get('avg_response_time_hrs', 0):.2f}")
                st.metric("Missing Ratings", stats.get("missing_customer_rating", 0))
            with col3:
                st.metric("Avg Resolution Time (hrs)", f"{stats.get('avg_resolution_time_hrs', 0):.2f}")
                st.metric("Avg Rating", f"{stats.get('avg_customer_rating', 0):.2f}")

            st.subheader("By Status")
            if "by_status" in stats:
                df_status = pd.DataFrame(list(stats["by_status"].items()), columns=["Status", "Count"])
                st.bar_chart(df_status.set_index("Status"))

            st.subheader("By Priority")
            if "by_priority" in stats:
                df_priority = pd.DataFrame(list(stats["by_priority"].items()), columns=["Priority", "Count"])
                st.bar_chart(df_priority.set_index("Priority"))

            st.subheader("By Category")
            if "by_category" in stats:
                df_cat = pd.DataFrame(list(stats["by_category"].items()), columns=["Category", "Count"])
                st.bar_chart(df_cat.set_index("Category"))

            st.subheader("By Agent")
            if "by_agent" in stats:
                df_agent = pd.DataFrame(list(stats["by_agent"].items()), columns=["Agent", "Count"])
                st.bar_chart(df_agent.set_index("Agent"))

            st.subheader("Date Range")
            if "date_range" in stats:
                st.write(f"From: {stats['date_range']['min']}")
                st.write(f"To: {stats['date_range']['max']}")
        else:
            st.warning("Could not load statistics")

    with tab4:
        st.header("Example Queries")
        examples = [
            "How many tickets are currently open?",
            "Which agent resolved the most tickets this month?",
            "Show me all Critical tickets not resolved within 12 hours.",
            "What is the average customer rating for Technical category tickets?",
            "Are there any anomalies in resolution times this week?",
            "How many critical tickets are unresolved?",
            "Which agent has the lowest average customer rating?",
            "What percentage of tickets are escalated?",
            "How many Technical tickets are open?",
            "What is the average resolution time for resolved Billing tickets?",
            "List unresolved Critical tickets.",
            "Which category has the highest average resolution time?",
        ]
        
        for i, ex in enumerate(examples):
            if st.button(f"📝 {ex}", key=f"ex_{i}"):
                st.session_state.query_input = ex
                st.rerun()

if __name__ == "__main__":
    main()