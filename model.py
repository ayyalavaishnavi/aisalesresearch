import streamlit as st
import requests
from bs4 import BeautifulSoup
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
import os
import re
from fill_template import fill_word_template

# Set API Keys securely
os.environ["GROQ_API_KEY"] = "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"

# Google Search Function
def google_search(query):
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    for g in soup.find_all('div', class_='tF2Cxc'):
        link = g.find('a')['href']
        return link
    return None

# Scrape Company Details
def scrape_company_website(company_name):
    company_info = {
        "company_name": company_name,
        "address": "Not Available",
        "employee_count": "Not Available",
        "annual_revenue": "Not Available",
        "leadership_changes": "Not Available",
        "recent_news": "Not Available",
        "recent_funding": "Not Available",
        "current_erp": "Not Available",
        "recent_job_postings": "Not Available",
        "phone_number": "Not Available",
        "sic_codes": "Not Available"
    }

    company_website = google_search(f"{company_name} official site")
    if company_website:
        try:
            response = requests.get(company_website, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")

            phone_match = re.search(r'(\+?\d{1,3}[-.\s]??\d{1,4}[-.\s]??\d{1,4}[-.\s]??\d{1,9})', soup.text)
            if phone_match:
                company_info["phone_number"] = phone_match.group(0)

            address_match = re.search(r'\d{1,5}\s\w+\s\w+,\s\w+,\s[A-Z]{2}\s\d{5}', soup.text)
            if address_match:
                company_info["address"] = address_match.group(0)

            job_postings = [job.text for job in soup.find_all("a") if "SAP" in job.text or "ERP" in job.text]
            company_info["recent_job_postings"] = ", ".join(job_postings) if job_postings else "No SAP job postings found."

        except Exception as e:
            st.warning(f"Failed to scrape website: {e}")

    return company_info

# AI Report Generation
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)

prompt_template = PromptTemplate(
    input_variables=["company_name", "scraped_data"],
    template="""
    **Company Report**

    ## Company Overview
    - **Company Name:** {company_name}
    - **Address:** {scraped_data[address]}
    - **Employee Count:** {scraped_data[employee_count]}
    - **Annual Revenue:** {scraped_data[annual_revenue]}

    ## Recent Developments
    - **Leadership Changes:** {scraped_data[leadership_changes]}
    - **Recent News:** {scraped_data[recent_news]}
    - **Recent Job Postings:** {scraped_data[recent_job_postings]}

    ## Financial & Industry Insights
    - **Recent Funding:** {scraped_data[recent_funding]}
    - **ERP System:** {scraped_data[current_erp]}
    - **SIC Codes:** {scraped_data[sic_codes]}

    ## Contact Information
    - **Phone:** {scraped_data[phone_number]}
    - **Address:** {scraped_data[address]}
    """
)

def generate_summary(company_name, scraped_data):
    prompt = prompt_template.format(company_name=company_name, scraped_data=scraped_data)
    response = llm.invoke(prompt)
    return response.content.strip()

# Streamlit UI
st.set_page_config(page_title="AI Sales Chatbot", page_icon="🤖", layout="wide")
st.sidebar.title("ℹ️ Instructions")
st.sidebar.write("Enter a company name to fetch insights and generate a structured summary.")


st.sidebar.title("🔍 Search History")

st.title("💬 AI Sales Chatbot")

# Initialize session state for chat history
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []

# Add a deselect option
if "selected_company" not in st.session_state:
    st.session_state["selected_company"] = None

# Sidebar radio buttons for company selection
selected_company = st.sidebar.radio(
    "Click a company to reload report:",
    st.session_state["search_history"],
    index=st.session_state["search_history"].index(st.session_state["selected_company"]) if st.session_state["selected_company"] else None
)

# Add a 'Deselect' button to clear the selection
if st.sidebar.button("Deselect"):
    st.session_state["selected_company"] = None
    st.rerun()

# Store the selected company in session state
st.session_state["selected_company"] = selected_company if selected_company else None

# Display the selected company's report if chosen from history
if selected_company:
    st.write(f"### 📄 Report for {selected_company}")
    if selected_company in st.session_state:
        st.markdown(st.session_state[selected_company])
    else:
        st.warning("No previous report found.")

# User input
user_input = st.chat_input("Enter a company name to generate a report...")

if user_input:
    if user_input not in st.session_state["search_history"]:
        st.session_state["search_history"].append(user_input)

    with st.spinner(f"🔍 Searching for **{user_input}**..."):
        company_info = scrape_company_website(user_input)

    with st.spinner("Generating report..."):
        report = generate_summary(user_input, company_info)

    # Store report in session
    st.session_state[user_input] = report

    # Display new report
    st.write(f"### 📄 Report for {user_input}")
    st.markdown(report)

    # Generate Word document
    template_path = "/Users/vaishnaviayyala/Desktop/US Consulting/AI Sales Research/Model/templates/ModelTemplate.docx"
    doc_file = fill_word_template(template_path, report)
    
    # Download Button
    st.download_button(
        label="📄 Download Report",
        data=doc_file,
        file_name=f"{user_input}_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )