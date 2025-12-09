# CS 372 Final Project: Duke Net Nutrition AI Assistant SETUP
#### This application is deployed. Access here: https://duke-nutrition-app.streamlit.app/

## To run locally:
### Prerequisites

- Python 3.8 or higher
- pip package manager
- OpenAI API key (Get one here)
- Git (for cloning repository)
- 4GB RAM minimum
- 2GB free disk space

### Installation Steps
**1. Clone the Repository: https://github.com/hwang0/duke-nutrition-app**
- git clone https://github.com/hwang0/duke-nutrition-app
- cd duke-nutrition-app

**2. Install Python Dependencies**
- pip install -r requirements.txt

**3. Set up OpenAPI Key**
- Create one here!: https://platform.openai.com/api-keys
- In your terminal, paste `export OPENAI_API_KEY="YOUR-ACTUAL-KEY-HERE"`
 
**4. Run the application**
- Run `streamlit run app.py`
- This will load menu data from data/menu_processed.json, load pre-computed embeddings from models/menu_embeddings.npy, download embedding model on first run (~90MB, one-time), launch your browser at http://localhost:8501

**5. Test functionality**
- Test the example queries provided and have fun!

### Example Testing
**Quick Verification (5 minutes)**
1. Visit: https://duke-nutrition-app.streamlit.app/
2. Test query: "High protein dinner for cutting"
3. Follow-up: "What about vegan options?"
4. Verify dietary filter persists in sidebar
