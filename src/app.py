import streamlit as st
import json
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from openai import OpenAI
import os
from rag_class import DukeNutritionRAG
import time

if 'last_call_time' not in st.session_state:
    st.session_state.last_call_time = 0

def rate_limit(seconds=3):
    now = time.time()
    if now - st.session_state.last_call_time < seconds:
        st.warning("Please wait a moment before making another request.")
        st.stop()
    st.session_state.last_call_time = now


os.environ['TRANSFORMERS_CACHE'] = './model_cache'


st.set_page_config(
    page_title="Duke Nutrition Assistant",
    page_icon="🍽️",
    layout="wide"
)

#Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #012169;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .recommendation-box {
        background-color: #1e1e1e;
        border-left: 4px solid #012169;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 8px;
        color: #e0e0e0;
        line-height: 1.6;
    }
    .user-message {
        background-color: #012169;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .assistant-message {
        background-color: #1e1e1e;
        border-left: 4px solid #012169;
        color: #e0e0e0;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .nutrition-tag {
        display: inline-block;
        background-color: #012169;
        color: white;
        padding: 0.3rem 0.6rem;
        border-radius: 12px;
        margin: 0.2rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_rag_system():
    """Load RAG system (cached for performance)"""
    
  #  st.write(" Step 1/5: Loading menu data...")
    with open('menu_processed.json', 'r') as f:
        data = json.load(f)
    items = data["items"]
    documents = data["documents"]
  #  st.write(" Menu data loaded!")
    
 #   st.write(" Step 2/5: Loading embeddings...")
    menu_embeddings = np.load('menu_embeddings.npy')
  #  st.write(" Embeddings loaded!")
    
  #  st.write(" Step 3/5: Downloading embedding model (this takes 2-3 mins)...")
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_tokenizer = AutoTokenizer.from_pretrained(model_name)
    embedding_model = AutoModel.from_pretrained(model_name)
  #  st.write(" Embedding model downloaded!")
    
   #st.write(" Step 4/5: Setting up device...")
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    
    embedding_model = embedding_model.to(device)
  #  st.write(f" Using device: {device}")
    
  #  st.write(" Step 5/5: Initializing RAG system...")
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found!")
        st.stop()
    
    client = OpenAI(api_key=api_key)
    
    rag = DukeNutritionRAG(
        client=client,
        embeddings=menu_embeddings,
        documents=documents,
        items=items,
        embedding_model=embedding_model,
        embedding_tokenizer=embedding_tokenizer,
        device=device
    )
    
  #  st.write(" RAG system ready!")
    return rag, items

#Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

#Load RAG system
try:
    rag, items = load_rag_system()
#    st.success(" System loaded successfully")
except Exception as e:
    st.error(f" Error loading system: {str(e)}")
    st.exception(e)
    st.stop()

#Header
st.markdown('<div class="main-header">🍽️ Duke Nutrition Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-powered meal recommendations from Duke dining hall items!</div>', unsafe_allow_html=True)

#Sidebar
with st.sidebar:
    st.header("ⓘ About")
    st.write("This RAG system uses semantic search + GPT-4 to recommend healthy meals based on your nutrition goals.")
    st.write("If you have dietary constraints, please always be sure to double check the recommendations before consuming!")
    
    st.header("System Stats")
    #st.metric("Total Menu Items", f"{len(items):,}")
    unique_restaurants = len(set(item['restaurant'] for item in items if item.get('restaurant')))
    st.metric("Dining Locations", unique_restaurants)
    
    st.header("Example Queries")
    example_queries = [
        "High protein dinner for cutting",
        "Vegan protein sources at Sprout",
        "Keto friendly meal",
        "Post-workout recovery meal",
        "High fiber breakfast",
        "High calorie protein meal for bulking"
    ]
    
    for ex_query in example_queries:
        if st.button(ex_query, key=f"ex_{ex_query}"):
            st.session_state['query_input'] = ex_query
    
    st.markdown("---")
    st.header("Conversation")
    st.metric("Messages", len(st.session_state.messages))
    
    #Show active filters
    active_filters = []
    if rag.dietary_requirement:
        active_filters.append(f" {rag.dietary_requirement.title()}")
    if rag.nutrition_goal:
        active_filters.append(f"{rag.nutrition_goal.title()}")
    if rag.excluded_restaurants:
        for restaurant in rag.excluded_restaurants:
            active_filters.append(f" No {restaurant}")
    
    if active_filters:
        st.info("**Active Filters:**\n" + "\n".join([f"- {f}" for f in active_filters]))
    
    if st.button(" Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_result = None
        rag.conversation_history = []
        rag.dietary_requirement = None
        rag.excluded_restaurants = []  
        rag.nutrition_goal = None   
        st.session_state["query_input"] = ""
        st.rerun()

#Display conversation history (ONLY PAST MESSAGES, not the current one)
if len(st.session_state.messages) > 2:  #Only show if there are previous conversations
    st.markdown("###  Conversation History")
    # Show all messages EXCEPT the last 2 (which are the current query/response)
    for msg in st.session_state.messages[:-2]:
        if msg['role'] == 'user':
            st.markdown(f'<div class="user-message"> You: {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="assistant-message"> Assistant: {msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown("---")

#Main interface
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""

query = st.text_area(
    "🔍 What are your nutrition goals?",
    value=st.session_state["query_input"],
    placeholder="e.g., I need high protein for cutting",
    height=100,
    help="Ask a question or follow up on previous recommendations!",
    key="query_input",
)

#Simple options - just conversation context checkbox
use_conversation_context = st.checkbox("Use conversation context", value=True, 
                                        help="Enable multi-turn conversation with memory")

#Get recommendations button
if st.button("Get Recommendations", type="primary", use_container_width=True):
    query = st.session_state.get("query_input", "")
    if not query.strip():
        st.warning("Please enter a query!")
    else:
        with st.spinner("Finding the best meals for you..."):
            try:
                #ALWAYS get exactly 3 recommendations
                rate_limit(seconds=3)
                result = rag.ask(
                    query, 
                    k=3,  
                    use_history=use_conversation_context,
                    verbose=False
                )
                
                #store result in session state
                st.session_state.last_result = result
                
                #Add to conversation history
                st.session_state.messages.append({"role": "user", "content": query})
                st.session_state.messages.append({"role": "assistant", "content": result['response']})
                
                #clear query box
                st.session_state['query'] = ''
                st.rerun()
                
            except Exception as e:
                st.error(f"Error getting recommendations: {str(e)}")
                st.exception(e)

#Display last result BELOW the query box
if st.session_state.last_result:
    result = st.session_state.last_result
    
    st.markdown("---")
    
    st.markdown("### Recommendations")
    st.markdown(f'<div class="recommendation-box">{result["response"]}</div>', unsafe_allow_html=True)
    
    #Display detailed nutrition for ALL 3 items
    st.markdown("### Detailed Nutrition Information")
    
    for i, item_result in enumerate(result['retrieved_items'], 1):
        item = item_result['item']
        
        #All expanded by default
        with st.expander(f"**{i}. {item['item_name']}** at {item['restaurant']}", expanded=True):
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Calories", f"{item.get('calories', 'N/A')}")
                st.metric("Protein", f"{item.get('protein_g', 'N/A')}g")
            
            with col_b:
                st.metric("Carbs", f"{item.get('total_carbs_g', 'N/A')}g")
                st.metric("Fat", f"{item.get('total_fat_g', 'N/A')}g")
            
            with col_c:
                st.metric("Fiber", f"{item.get('fiber_g', 'N/A')}g")
                st.metric("Sugar", f"{item.get('sugars_g', 'N/A')}g")
            
            # Show dietary labels
            if item.get('dietary_labels'):
                st.markdown("**Dietary Labels:**")
                labels = str(item['dietary_labels']).split(';')
                label_html = ''.join([f'<span class="nutrition-tag">{label.strip()}</span>' for label in labels if label.strip()])
                st.markdown(label_html, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>CS 372 Final Project | Duke University</p>
    <p>Multi-turn conversation with context tracking enabled</p>
</div>
""", unsafe_allow_html=True)