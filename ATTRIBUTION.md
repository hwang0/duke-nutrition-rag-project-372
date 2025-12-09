# CS 372 Final Project: Duke Net Nutrition AI Assistant ATTRIBUTION

Attribution of data sources, AI assistance, external libraries, and resources used in this project.

This project was developed with assistance from **Claude AI (Anthropic)** as a development aid, similar to using Stack Overflow, documentation or pair programming.

### **AI Assistance Summary**

**What AI Helped With:**
- Code structure and organization suggestions
- Debugging assistance and error resolution
- Comment generation and code documentation
- Visualization code for evaluation plots
- Web scraping script structure and error handling
- Ratio generations for macro nutrients
- Streamlit UI components and layout suggestions

### **Detailed Attribution by Component**

**1. Data Collection & Preprocessing (Notebook 1)**
- **AI Assistance**: Web scraping script structure, CSV parsing code, error handling patterns, data cleaning
- **My work**: Identified data sources, designed preprocessing pipeline, defined feature engineering approach

**2. Embedding Generation (Notebook 2)**
- **AI Assistance**: Debugging assistance, code comments, numerical calculations for ratio bonus system
- **My work**: Selected embedding model (all-MiniLM-L6-v2), designed batch processing, validated embedding quality

**3. RAG System (Notebook 3)**
- **AI Assistance**: Class structure suggestions, conversation history management patterns, 
- **My work**: **Designed entire nutrition-aware retrieval system**, implemented ratio bonus algorithm, defined filtering logic,, designed multi-turn conversation flow, created few-shot examples

**4. Evaluation (Notebook 4)**
- **AI Assistance**: Matplotlib/Seaborn plotting code, baseline class templates
- **My work**: Designed 3 distinct metrics, created test dataset with ground truth, defined success criteria for each nutrition goal, designed ablation study, analyzed results and identified failure modes

**5. Streamlit App (app.py)**
- **AI Assistance**: Streamlit component syntax, CSS styling, session state management
- **My work**: UI/UX design decisions, example query selection, information architecture

**6. Documentation**
- **AI Assistance**: Markdown formatting, template structure and sentence refining for README/SETUP/ATTRIBUTION
- **My work**: All content, analysis, explanations, and technical decisions

AI was mainly used as a coding assistant speed up implementation of standard patterns, debug syntax errors and runtime issues, format, document, and clean code
