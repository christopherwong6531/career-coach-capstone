import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from fpdf import FPDF

# --- PAGE CONFIG (Must be first) ---
st.set_page_config(page_title="AI Career Coach", page_icon="🚀", layout="centered")

# ==========================================
#        DRAW THE UI IMMEDIATELY
# ==========================================
st.title("🚀 Brutally Honest AI Career Coach")
st.markdown("This multi-agent system will roast your resume, find the hidden gold, and rewrite it perfectly for your dream job.")

# --- 0. SETUP GEMINI API (Now with a spinner!) ---
@st.cache_resource 
def setup_ai():
    import os
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    MODEL_ID = None
    try:
        available_models = list(client.models.list())
        for m in available_models:
            if "flash" in m.name.lower():
                MODEL_ID = m.name.split("/")[-1] 
                break
        if not MODEL_ID and available_models:
            MODEL_ID = available_models[0].name.split("/")[-1]
    except:
        MODEL_ID = "gemini-1.5-flash"
    return client, MODEL_ID

with st.spinner("Connecting to Google AI..."):
    client, MODEL_ID = setup_ai()

# --- STATE MANAGEMENT ---
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.safe_resume = ""
    st.session_state.job_description = ""
    st.session_state.roast = ""
    st.session_state.hype = ""
    st.session_state.final_resume = ""

# --- SKILLS (PII, Scraper, PDF) ---
def scrub_resume_pii(resume_text):
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', resume_text)
    text = re.sub(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[REDACTED_PHONE]', text)
    return text

def scrape_job_posting(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)[:5000]
    except:
        return "Software Engineer. Must know Python, GCP, and AI Agents. High-impact tools."

def create_pdf(resume_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11) 
    clean_text = resume_text.replace('**', '').replace('*', '-')
    clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, text=clean_text)
    pdf.output("Optimized_Resume.pdf")
    return "Optimized_Resume.pdf"

# --- LLM HELPER ---
def call_llm(system_instruction, user_content):
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=user_content,
        config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.7)
    )
    return response.text

# --- STEP 1: INPUTS ---
if st.session_state.step == 1:
    st.header("Step 1: The Raw Materials")
    user_resume = st.text_area("Paste your current resume here:", height=200, placeholder="Wayland Wong\nwayland@email.com\nI did vibe coding and synergized paradigms...")
    job_link = st.text_input("Paste the Job URL you want:", placeholder="https://www.ycombinator.com/jobs/role/software-engineer")
    
    if st.button("🔥 Roast My Resume", type="primary"):
        if user_resume and job_link:
            with st.spinner("Scrubbing PII & Scraping the web..."):
                st.session_state.safe_resume = scrub_resume_pii(user_resume)
                st.session_state.job_description = scrape_job_posting(job_link)
            
            with st.spinner("Agent 1 (The Roaster) is tearing it apart..."):
                roast_prompt = "You are a brutally honest career coach. Roast this resume against the job description. Be ruthless. Output a bulleted list."
                roaster_input = f"RESUME:\n{st.session_state.safe_resume}\n\nJOB:\n{st.session_state.job_description}"
                st.session_state.roast = call_llm(roast_prompt, roaster_input)
                
            with st.spinner("Agent 2 (The Hype Person) is looking for hidden gold..."):
                hype_prompt = "You are the Hype Person. Review the Roaster's critique and the resume. Draft 3 specific questions to ask the user to uncover the actual metrics behind their weak bullets."
                hype_input = f"RESUME:\n{st.session_state.safe_resume}\n\nROAST:\n{st.session_state.roast}"
                st.session_state.hype = call_llm(hype_prompt, hype_input)
                
            st.session_state.step = 2
            st.rerun() # Refresh the page
        else:
            st.error("Please provide both your resume and a job link!")

# --- STEP 2: HUMAN IN THE LOOP ---
if st.session_state.step == 2:
    st.header("Step 2: The Assessment")
    
    st.error("🔥 **THE ROASTER SAYS:**\n\n" + st.session_state.roast)
    st.info("✨ **THE HYPE PERSON SAYS:**\n\n" + st.session_state.hype)
    
    st.markdown("### 💬 Your Turn!")
    user_answers = st.text_area("Answer the Hype Person's questions here to provide metrics & context:")
    
    if st.button("📝 Write My Final Resume", type="primary"):
        if user_answers:
            with st.spinner("Agent 3 (The ATS Whisperer) is crafting your masterpiece..."):
                writer_prompt = "You are the ATS Whisperer. Write a flawless, ATS-optimized resume tailored to the job using the original resume and the user's new metrics. Output ONLY the plain text of the new resume."
                writer_input = f"ORIGINAL RESUME:\n{st.session_state.safe_resume}\n\nJOB:\n{st.session_state.job_description}\n\nUSER METRICS:\n{user_answers}"
                st.session_state.final_resume = call_llm(writer_prompt, writer_input)
                
            st.session_state.step = 3
            st.rerun()
        else:
            st.warning("Please answer the Hype Person's questions first!")

# --- STEP 3: EXPORT ---
if st.session_state.step == 3:
    st.header("Step 3: Your Final Resume")
    st.success("✅ Your highly optimized resume is ready!")
    
    st.text_area("Final Resume Output:", st.session_state.final_resume, height=300)
    
    # Trigger the PDF Skill
    pdf_filename = create_pdf(st.session_state.final_resume)
    
    # Streamlit Download Button
    with open(pdf_filename, "rb") as pdf_file:
        st.download_button(
            label="💾 Download as PDF",
            data=pdf_file,
            file_name="My_ATS_Optimized_Resume.pdf",
            mime="application/pdf"
        )
    
    # Reset button
    if st.button("Start Over"):
        st.session_state.step = 1
        st.rerun()
