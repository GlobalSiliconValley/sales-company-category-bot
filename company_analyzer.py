import streamlit as st
import openai
import os
import json

# Configure OpenRouter API - using streamlit secrets for deployment
# try:
#     # Try to get API key from Streamlit secrets first (for deployment)
#     api_key = st.secrets["OPENROUTER_API_KEY"]
# except:
    # Fall back to environment variable (for local development)
api_key = os.getenv("OPENROUTER_API_KEY")

# Configure OpenAI client for older version (0.28.1)
openai.api_key = api_key
openai.api_base = "https://openrouter.ai/api/v1"

# App configuration
st.set_page_config(
    page_title="Company Analysis Tool",
    page_icon="🏢",
    layout="wide"
)

# Title and description
st.title("🏢 Company Analysis Tool")
st.write("Analyze companies and assign team members based on education sector")

# Sidebar for model selection
st.sidebar.header("Settings")
model_options = [
    "openai/gpt-4o",
    "meta-llama/llama-3.2-3b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free"
]
selected_model = st.sidebar.selectbox("Select Model", model_options)

# Team assignment mapping
TEAM_ASSIGNMENTS = {
    "K-12": "Mitch",
    "Higher Education": "Mitch", 
    "K-12 + Higher Education": "Mitch",
    "Workforce Learning": "Sam",
    "Corporate Development": "Sam",
    "Workforce + Corporate": "Sam",
    "Other": "To be assigned"
}

# Your analysis prompt template
ANALYSIS_PROMPT = """
You are an expert at analyzing companies in the education sector. 

Please analyze the following company and categorize it based on which sector of education their products and services serve:

Company: {company_name}
Description: {company_description}

Please provide your analysis in the following JSON format:
{{
    "company_name": "Company Name",
    "primary_sectors": ["list of primary education sectors"],
    "secondary_sectors": ["list of secondary education sectors"],
    "reasoning": "Brief explanation of your analysis",
    "confidence": "High/Medium/Low"
}}

Education sector categories:
- K-12: Elementary, middle, and high school education
- Higher Education: Universities, colleges, community colleges
- Workforce Learning: Professional training, skill development, corporate training
- Corporate Development: Leadership development, executive education
- Other: EdTech tools, platforms, or services that don't fit above categories

Be specific and provide clear reasoning for your categorization.
"""

def get_team_assignment(sectors):
    """Determine team assignment based on education sectors"""
    if not sectors:
        return "To be assigned"
    
    # Convert to set for easier matching
    sector_set = set(sectors)
    
    # Check for combinations
    if {"K-12", "Higher Education"}.issubset(sector_set):
        return "Mitch"
    elif {"Workforce Learning", "Corporate Development"}.issubset(sector_set):
        return "Sam"
    elif "K-12" in sector_set or "Higher Education" in sector_set:
        return "Mitch"
    elif "Workforce Learning" in sector_set or "Corporate Development" in sector_set:
        return "Sam"
    else:
        return "To be assigned"

def analyze_company(company_name, company_description, model):
    """Analyze company using OpenRouter API"""
    try:
        # Format the prompt
        prompt = ANALYSIS_PROMPT.format(
            company_name=company_name,
            company_description=company_description or "No description provided"
        )
        
        # Make API call using older OpenAI library syntax
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert education sector analyst. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        # Parse response
        content = response.choices[0].message.content
        
        # Try to extract JSON from response
        try:
            # Find JSON in response
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]
            analysis = json.loads(json_str)
            return analysis
        except:
            # If JSON parsing fails, return structured response
            return {
                "company_name": company_name,
                "primary_sectors": ["Other"],
                "secondary_sectors": [],
                "reasoning": content,
                "confidence": "Low"
            }
            
    except Exception as e:
        st.error(f"Error analyzing company: {str(e)}")
        return None

# Main interface
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Company Information")
    
    # Input fields
    company_name = st.text_input("Company Name", placeholder="e.g., Khan Academy")
    company_description = st.text_area(
        "Company Description (optional)", 
        placeholder="Brief description of what the company does...",
        height=100
    )
    
    # Analysis button
    if st.button("🔍 Analyze Company", type="primary"):
        if company_name:
            with st.spinner("Analyzing company..."):
                analysis = analyze_company(company_name, company_description, selected_model)
                
                if analysis:
                    # Store in session state
                    st.session_state.last_analysis = analysis
                    
                    # Display results
                    st.success("Analysis complete!")
                    
                    # Results section
                    st.header("📊 Analysis Results")
                    
                    col_result1, col_result2 = st.columns(2)
                    
                    with col_result1:
                        st.subheader("Education Sectors")
                        if analysis.get('primary_sectors'):
                            st.write("**Primary:**", ", ".join(analysis['primary_sectors']))
                        if analysis.get('secondary_sectors'):
                            st.write("**Secondary:**", ", ".join(analysis['secondary_sectors']))
                    
                    with col_result2:
                        st.subheader("Team Assignment")
                        all_sectors = analysis.get('primary_sectors', []) + analysis.get('secondary_sectors', [])
                        assigned_member = get_team_assignment(all_sectors)
                        st.write(f"**Assigned to:** {assigned_member}")
                        st.write(f"**Confidence:** {analysis.get('confidence', 'Medium')}")
                    
                    # Reasoning
                    st.subheader("Analysis Reasoning")
                    st.write(analysis.get('reasoning', 'No reasoning provided'))
        else:
            st.warning("Please enter a company name")

with col2:
    st.header("Team Assignments")
    st.write("**Current assignment rules:**")
    
    for sectors, member in TEAM_ASSIGNMENTS.items():
        st.write(f"• {sectors} → {member}")

# History section
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# Add to history if we have a recent analysis
if hasattr(st.session_state, 'last_analysis') and st.session_state.last_analysis:
    # Check if this analysis is already in history
    analysis = st.session_state.last_analysis
    if not any(h.get('company_name') == analysis.get('company_name') for h in st.session_state.analysis_history):
        all_sectors = analysis.get('primary_sectors', []) + analysis.get('secondary_sectors', [])
        st.session_state.analysis_history.append({
            'company_name': analysis.get('company_name'),
            'sectors': all_sectors,
            'assigned_to': get_team_assignment(all_sectors),
            'confidence': analysis.get('confidence', 'Medium')
        })

# Display history
if st.session_state.analysis_history:
    st.header("📈 Analysis History")
    for i, item in enumerate(reversed(st.session_state.analysis_history[-10:])):  # Show last 10
        with st.expander(f"{item['company_name']} → {item['assigned_to']}"):
            st.write(f"**Sectors:** {', '.join(item['sectors'])}")
            st.write(f"**Confidence:** {item['confidence']}")

# Instructions
st.sidebar.header("Instructions")
st.sidebar.write("""
1. Enter company name (required)
2. Add description (optional but recommended)
3. Select AI model from dropdown
4. Click 'Analyze Company'
5. Review results and team assignment
""")

st.sidebar.header("API Setup")
st.sidebar.write("""
**For local development:**
Create a `.env` file with:
```
OPENROUTER_API_KEY=your_key_here
```

**For Streamlit Cloud deployment:**
Add your API key in the Streamlit secrets section as:
```
OPENROUTER_API_KEY = "your_key_here"
```
""")