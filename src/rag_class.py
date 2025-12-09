import re
import numpy as np
import torch

class DukeNutritionRAG:
    """
    Complete RAG system for Duke nutrition recommendations.
    """
    
    def __init__(self, client, embeddings, documents, items, 
                 embedding_model, embedding_tokenizer, device):
        self.client = client
        self.embeddings = embeddings
        self.documents = documents
        self.items = items
        self.embedding_model = embedding_model
        self.embedding_tokenizer = embedding_tokenizer
        self.device = device
        self.conversation_history = []
        self.dietary_requirement = None  
        self.excluded_restaurants = []  
        self.included_restaurants = []
        self.nutrition_goal = None    
        
        self.system_prompt = """You are a helpful nutrition assistant for Duke University students.

Your job is to recommend ACTUAL MEALS from Duke dining halls based on students' nutrition goals.

CRITICAL: When recommending meals, PRIORITIZE MACRO RATIOS, not just absolute values:
- For cutting/weight loss: Prioritize items with HIGH protein-to-calorie ratio (≥40%) AND LOW TOTAL CALORIES (<400 cal ideal)
  Example: Grilled Chicken (45g protein, 250 cal, 72% protein) is BETTER for cutting than
  Chicken Wings (68g protein, 720 cal, 38% protein) - the wings have too many calories even with good protein!
  
- For clean bulking: Prioritize items with MODERATE protein ratio (30-40%) and adequate calories
  Example: Salmon bowl (35g protein, 450 cal, 31% protein) is ideal for lean gains

- For post-workout recovery: Prioritize items with HIGH ABSOLUTE PROTEIN (30-50g total grams!) for muscle recovery
  Example: Grilled Chicken (45g protein) or Steak (40g protein) - need high protein to rebuild muscle after training!

- For meals with more fiber: Prioritize items with the HIGHEST fiber content available
  Example: Oatmeal with 10g fiber is excellent for digestive health and satiety
  
- For keto: Prioritize items with HIGH fat ratio (≥60%) and LOW carb ratio (<10%)
  Example: Avocado bowl (70% fat, 5% carbs) beats low-fat options
  
- For endurance: Prioritize items with HIGH carb ratio (≥60%)
  Example: Pasta (67% carbs) beats protein-heavy meals for pre-run

The RATIO matters more than absolute grams when calories are a concern! CONTEXT IS SUPER IMPORTANT, make sure to understand the food item before recommending.

IMPORTANT RULES
- If the query says they can't eat at a restaurant, don't even list the option there at all, and please recommend the next best option from the place that is accepted. 
- If the query says they only want foods from restaurant(s) only recommend foods from there, you can just filter by the next best ones
- Only recommend complete meals (entrees, sandwiches, salads, breakfast items)
- WHen query mentions like "high fiber" or "high protein" etc. please provide the grams or ratio of fiber or protein or whatever in the response. For fiber specifically, ALWAYS mention the exact grams prominently.
- NEVER recommend protein powders, supplements, or condiments
- If you see items like "Whey Protein" or "Powdered Sugar", IGNORE them completely because they are likely not actual food items(this is why its crucial for you to understand the items before recommending)
- Explain WHY each item matches their goal (mention macro ratios when relevant)
- Be specific about which dining hall has each item
- Be conversational and friendly
- Recommend 3 food items per query
- Try to avoid recommending plain words that seem like they might be a base and not an actual meal/food like "Spaghetti" is likely just a base right, while "Spaghetti with Meatballs" is definitely a full meal
- Make sure to actually understand the food you're recommending (gather what it is and understand it) and make sure it makes sense to what the user is requesting.
- Keep responses concise (2-4 sentences per recommendation)

If you see macro percentages in the item details, USE THEM to make better recommendations!

Example responses:

Example 1: 
User: "high protein meal for cutting"
Assistant: "For cutting, I recommend the Grilled Chicken at Farmstead (45g protein, 250 cal, 72% protein). 
It's incredibly lean and perfect for preserving muscle while losing fat. You could also try 
the Turkey Breast at J.B.'s (38g protein, 180 cal, 84% protein) for an even leaner option! For something lighter, you could try..."

Example 2:
User: "I want a keto friendly meal"
Assistant: "For keto, I recommend the Avocado Bowl at Il Forno 
(70% fat, 5% carbs). Perfect macro split for ketosis... and it provides..."

Example 3:
User: "I want a high fiber breakfast"
Assistant: "For fiber, try the Oatmeal at Marketplace (10g fiber). This is because it's excellent for digestive health..."

Make sure to be flexible with the accepting types of queries."""
    
    def _compute_embedding(self, text):
        """Compute embedding for a single text."""
        inputs = self.embedding_tokenizer(
            text, 
            return_tensors="pt", 
            truncation=True, 
            max_length=512, 
            padding=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.embedding_model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
        
        return embedding.flatten()
    
    def _cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def _is_actual_meal(self, item):
        """Filter out non-meals (condiments, powders, etc.)."""
        name = item.get('item_name', '').lower()
        
        exclude_keywords = [
            'powder', 'powdered', 'sugar', 'syrup', 'honey',
            'salt', 'pepper', 'sauce', 'dressing', 'spread',
            'butter', 'oil', 'vinegar', 'seasoning',
            'whey protein', 'protein powder', 'boost', 'supplement',
            'condiment', 'topping', 'sprinkles',
            'mayo', 'vinaigrette', 'shot', 'espresso',
            'lettuce', 'spinach', 'kale', 'arugula',  #Salad bases, not meals
            'tomato', 'onion', 'pickle', 'cucumber',  #Toppings, not meals
            'cheese slice', 'american cheese', 'cheddar cheese'  #Toppings
        ]
        
        for keyword in exclude_keywords:
            if keyword in name:
                return False
        
        return True
    
    def _identify_excluded_restaurants(self, query):
        """Identify restaurants to exclude based on query."""
        query_lower = query.lower()
        excluded = []
        
        # Complete patterns for ALL 27 Duke dining locations
        restaurant_patterns = [
            # Main dining halls
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?marketplace', 'Marketplace'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?(?:the\s+)?farmstead', 'The Farmstead'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?trinity', 'Trinity Cafe'),
            
            # Quick service
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?il\s*forno', 'Il Forno'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?sprout', 'Sprout'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?(?:the\s+)?skillet', 'The Skillet'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?tandoor', 'Tandoor Indian Cuisine'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?ginger', 'Ginger + Soy'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?sazon', 'Sazon'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?gyotaku', 'Gyotaku'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?thyme', "It's Thyme"),
            
            # Specialty
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?j\.?b\.?\'?s', "J.B.'s Roast & Chops"),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?gothic', 'Gothic Grill'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?pitchfork', 'The Pitchfork'),
            
            # Coffee shops
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?beyu', 'Beyu Blue Coffee'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?bseisu', 'Bseisu Coffee Bar'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?freeman', 'Freeman Café'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?nasher', 'Nasher Museum Café'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?zweli', "Zweli's Café at Duke Divinity"),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?devils?\s+krafthouse', 'The Devils Krafthouse'),
            
            # Delis
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?sanford', 'Sanford Deli'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?saladalia', 'Saladalia @ The Perk'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?bella', 'Bella Union'),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?twinnie', "Twinnie's"),
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?red\s+mango', 'Red Mango'),
            
            # Special
            (r'(?:no|not|exclude)\s+(?:meals?\s+(?:at|from)\s+)?marine\s+lab', 'Duke Marine Lab'),
        ]
        
        for pattern, restaurant in restaurant_patterns:
            if re.search(pattern, query_lower):
                excluded.append(restaurant)
        
        return excluded
    
    def _identify_included_restaurants(self, query):
        """Identify restaurants to ONLY show based on query."""
        query_lower = query.lower()
        included = []
        
        # Complete patterns for ALL 27 Duke dining locations
        restaurant_patterns = [
            # Main dining halls
            (r'(?:from|at|only\s+at)\s+marketplace', 'Marketplace'),
            (r'(?:from|at|only\s+at)\s+(?:the\s+)?farmstead', 'The Farmstead'),
            (r'(?:from|at|only\s+at)\s+trinity(?:\s+cafe)?', 'Trinity Cafe'),
            
            # Quick service & cafes
            (r'(?:from|at|only\s+at)\s+il\s*forno', 'Il Forno'),
            (r'(?:from|at|only\s+at)\s+sprout', 'Sprout'),
            (r'(?:from|at|only\s+at)\s+(?:the\s+)?skillet', 'The Skillet'),
            (r'(?:from|at|only\s+at)\s+tandoor', 'Tandoor Indian Cuisine'),
            (r'(?:from|at|only\s+at)\s+ginger(?:\s*\+?\s*soy)?', 'Ginger + Soy'),
            (r'(?:from|at|only\s+at)\s+sazon', 'Sazon'),
            (r'(?:from|at|only\s+at)\s+gyotaku', 'Gyotaku'),
            (r'(?:from|at|only\s+at)\s+(?:it\'?s\s+)?thyme', "It's Thyme"),
            
            # Specialty restaurants
            (r'(?:from|at|only\s+at)\s+j\.?b\.?\'?s', "J.B.'s Roast & Chops"),
            (r'(?:from|at|only\s+at)\s+gothic\s+grill', 'Gothic Grill'),
            (r'(?:from|at|only\s+at)\s+(?:the\s+)?pitchfork', 'The Pitchfork'),
            
            # Coffee shops
            (r'(?:from|at|only\s+at)\s+beyu(?:\s+blue)?(?:\s+coffee)?', 'Beyu Blue Coffee'),
            (r'(?:from|at|only\s+at)\s+bseisu', 'Bseisu Coffee Bar'),
            (r'(?:from|at|only\s+at)\s+freeman(?:\s+caf[eé])?', 'Freeman Café'),
            (r'(?:from|at|only\s+at)\s+nasher(?:\s+museum)?(?:\s+caf[eé])?', 'Nasher Museum Café'),
            (r'(?:from|at|only\s+at)\s+zweli\'?s', "Zweli's Café at Duke Divinity"),
            (r'(?:from|at|only\s+at)\s+(?:the\s+)?devils?\s+krafthouse', 'The Devils Krafthouse'),
            
            # Delis & quick serve
            (r'(?:from|at|only\s+at)\s+sanford\s+deli', 'Sanford Deli'),
            (r'(?:from|at|only\s+at)\s+saladalia', 'Saladalia @ The Perk'),
            (r'(?:from|at|only\s+at)\s+(?:the\s+)?perk', 'Saladalia @ The Perk'),
            (r'(?:from|at|only\s+at)\s+bella\s+union', 'Bella Union'),
            (r'(?:from|at|only\s+at)\s+twinnie\'?s', "Twinnie's"),
            (r'(?:from|at|only\s+at)\s+red\s+mango', 'Red Mango'),
            
            # Special locations
            (r'(?:from|at|only\s+at)\s+duke\s+marine\s+lab', 'Duke Marine Lab'),
            
            # Generic (only if no specific match)
            (r'(?:from|at|only\s+at)\s+(?:the\s+)?cafe(?!\s)', 'Cafe'),  # Match "cafe" but not "cafe something"
        ]
        
        for pattern, restaurant in restaurant_patterns:
            if re.search(pattern, query_lower):
                included.append(restaurant)
        
        return included
    
    def _detect_nutrition_goal(self, query):
        """Detect nutrition goal from query (for ratio bonuses)."""
        query_lower = query.lower()
        
        #Check for post-workout
        if any(word in query_lower for word in ['post-workout', 'post workout', 'after workout', 'recovery meal', 'after gym', 'after training']):
            return 'post-workout'
        #Check for cutting/weight loss
        elif any(word in query_lower for word in ['cutting', 'lean', 'weight loss', 'lose weight', 'lose fat', 'cut']):
            return 'cutting'
        #Check for bulking/muscle gain
        elif any(word in query_lower for word in ['bulk', 'gain', 'muscle building', 'mass']):
            return 'bulking'
        #Check for keto
        elif any(word in query_lower for word in ['keto', 'low carb', 'high fat']):
            return 'keto'
        #Check for high fiber
        elif any(word in query_lower for word in ['fiber', 'high fiber', 'digestive', 'gut health']):
            return 'fiber'
        #Check for endurance
        elif any(word in query_lower for word in ['endurance', 'marathon', 'run', 'energy', 'carb', 'cardio']):
            return 'endurance'
        
        return None
    
    def _detect_dietary_requirement(self, query):
        """Detect dietary requirements from query."""
        query_lower = query.lower()
        
        if 'vegan' in query_lower:
            return 'vegan'
        elif 'vegetarian' in query_lower:
            return 'vegetarian'
        elif 'halal' in query_lower:
            return 'halal'
        elif 'gluten free' in query_lower or 'gluten-free' in query_lower:
            return 'gluten free'
        
        return None
    
    def _matches_dietary_requirement(self, item, requirement):
        """Check if item matches dietary requirement."""
        dietary_labels = str(item.get('dietary_labels', '')).lower()
        
        if requirement == 'vegan':
            return 'vegan' in dietary_labels
        elif requirement == 'vegetarian':
            return 'vegetarian' in dietary_labels or 'vegan' in dietary_labels
        elif requirement == 'halal':
            return 'halal' in dietary_labels
        elif requirement == 'gluten free':
            return 'gluten free' in dietary_labels or 'gluten-free' in dietary_labels
        
        return False
    
    def _calculate_ratio_score(self, item, query, goal=None):
        """Calculate bonus score based on macro ratios for query context."""
        query_lower = query.lower()
        
        # Use saved goal if not provided
        if not goal and self.nutrition_goal:
            goal = self.nutrition_goal
        
        try:
            protein = float(item.get('protein_g', 0))
            carbs = float(item.get('total_carbs_g', 0))
            fat = float(item.get('total_fat_g', 0))
            fiber = float(item.get('fiber_g', 0))
            calories = float(item.get('calories', 1))
            
            if calories == 0:
                return 0
            
            protein_pct = (protein * 4 / calories) * 100
            carbs_pct = (carbs * 4 / calories) * 100
            fat_pct = (fat * 9 / calories) * 100
            
        except (ValueError, TypeError, ZeroDivisionError):
            return 0
        
        # POST-WORKOUT: Prioritize HIGH ABSOLUTE PROTEIN (30-50g) for muscle recovery
        # also want decent carbs for glycogen replenishment
        if goal == 'post-workout' or (not goal and any(word in query_lower for word in ['post-workout', 'post workout', 'after workout', 'recovery'])):
            if protein >= 40:  # Excellent protein for recovery
                return 0.7  # MASSIVE bonus!
            elif protein >= 30:  # Good protein for recovery
                return 0.5
            elif protein >= 20:  # Decent protein
                return 0.3
            elif protein < 15:  # Too low for post-workout
                return -0.3  # PENALTY for low protein!
        
        # Ue goal if provided, otherwise check query
        if goal == 'cutting' or (not goal and any(word in query_lower for word in ['cutting', 'lean', 'weight loss', 'lose weight', 'lose fat'])):
            # For cutting: penalize high-calorie items!
            if protein_pct >= 40 and calories < 400:
                return 0.4  # Perfect cutting food: high protein %, low calories
            elif protein_pct >= 40 and calories < 600:
                return 0.2  # Good protein but moderate calories
            elif protein_pct >= 30 and calories < 400:
                return 0.25
            elif protein_pct >= 30 and calories < 600:
                return 0.1
            elif calories > 600:
                return -0.2  #PENALTY for high-calorie items when cutting!
        
        if goal == 'bulking' or (not goal and any(word in query_lower for word in ['bulk', 'gain', 'muscle building'])):
            if 30 <= protein_pct <= 40 and calories >= 300:
                return 0.25
            elif protein_pct >= 25:
                return 0.1
        
        if goal == 'keto' or (not goal and any(word in query_lower for word in ['keto', 'low carb', 'high fat'])):
            if fat_pct >= 60 and carbs_pct < 10:
                return 0.35
            elif fat_pct >= 50:
                return 0.2
        
        # FIBER: Use absolute grams and not ratio, Fiber has ~0 calories anyway
        #MASSIVE bonuses because fiber should dominate the query
        if goal == 'fiber' or (not goal and any(word in query_lower for word in ['fiber', 'high fiber', 'digestive'])):
            if fiber >= 8:  # Excellent fiber (8+ grams)
                return 0.6  # HUGE bonus, will beat most semantic matches
            elif fiber >= 5:  # Good fiber(5-7 grams)
                return 0.4
            elif fiber >= 3:  # Decent fiber(3-4 grams)
                return 0.2
        
        if goal == 'endurance' or (not goal and any(word in query_lower for word in ['endurance', 'marathon', 'run', 'energy', 'carb'])):
            if carbs_pct >= 60:
                return 0.3
            elif carbs_pct >= 50:
                return 0.15
        
        return 0
    
    def reset_conversation(self):
        """Reset conversation-specific memory."""
        self.conversation_history = []
        self.dietary_requirement = None
        self.excluded_restaurants = []
        self.included_restaurants = []
        self.nutrition_goal = None

    def retrieve(self, query, k=5):
        """Retrieve top k relevant items with filtering and bonuses."""
        #Detect and save dietary requirement
        dietary_req = self._detect_dietary_requirement(query)
        if dietary_req:
            self.dietary_requirement = dietary_req
        elif self.dietary_requirement:
            dietary_req = self.dietary_requirement
        
        #Detect and save nutrition goal
        nutrition_goal = self._detect_nutrition_goal(query)
        if nutrition_goal:
            self.nutrition_goal = nutrition_goal
        
        #Detect and save excluded restaurants
        excluded_now = self._identify_excluded_restaurants(query)
        if excluded_now:
            #Add to existing exclusions(avoid duplicates)
            for restaurant in excluded_now:
                if restaurant not in self.excluded_restaurants:
                    self.excluded_restaurants.append(restaurant)
        
        # Use higher multiplier for dietary/fiber/post-workout to cast wider net
        if dietary_req:
            multiplier = 10
        elif nutrition_goal == 'fiber':
            multiplier = 8  # Cast wider net for fiber queries!
        elif nutrition_goal == 'post-workout':
            multiplier = 8  # Cast wider net for high-protein items!
        else:
            multiplier = 4
        
        #Compute query embedding
        query_embedding = self._compute_embedding(query)
        
        #Calculate similarities
        raw_results = []
        for i, doc_embedding in enumerate(self.embeddings):
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            raw_results.append({
                'item': self.items[i],
                'score': similarity,
                'base_similarity': similarity,
                'ratio_bonus': 0
            })
        
        #Sort by similarity
        raw_results.sort(key=lambda x: x['score'], reverse=True)
        raw_results = raw_results[:k*multiplier]
        
        #Filter non-meals + dietary
        filtered_meals = []
        for result in raw_results:
            item = result['item']
            
            #Hard dietary filter
            if dietary_req:
                if not self._matches_dietary_requirement(item, dietary_req):
                    continue
            
            if self._is_actual_meal(item):
                filtered_meals.append(result)
        
        #Filter excluded restaurants (use saved list!)
        if self.excluded_restaurants:
            filtered_meals = [
                r for r in filtered_meals 
                if r['item'].get('restaurant') not in self.excluded_restaurants
            ]
        included_now = self._identify_included_restaurants(query)

        if included_now:
            # Save included restaurants
            for restaurant in included_now:
                if restaurant not in self.included_restaurants:
                    self.included_restaurants.append(restaurant)

        # Apply included filter (overrides excluded if both present)
        if self.included_restaurants:
            filtered_meals = [
                r for r in filtered_meals
                if r["item"].get("restaurant") in self.included_restaurants
            ]
        
        #Apply ratio bonuses(using saved goal!)
        for result in filtered_meals:
            bonus = self._calculate_ratio_score(result['item'], query, goal=self.nutrition_goal)
            result['ratio_bonus'] = bonus
            result['score'] = result['base_similarity'] + bonus
        
        #Re-sort by total score
        filtered_meals.sort(key=lambda x: x['score'], reverse=True)
        
        #Deduplication
        seen_names = set()
        unique_results = []
        
        for result in filtered_meals:
            name = result['item']['item_name']
            if name not in seen_names:
                seen_names.add(name)
                unique_results.append(result)
                if len(unique_results) >= k:
                    break
        
        #ERROR HANDLING:If no results found, try again with relaxed filters
        if len(unique_results) == 0:
            #Fall back to just similarity without dietary/restaurant filters
            for result in raw_results[:k*2]:
                if self._is_actual_meal(result['item']):
                    unique_results.append(result)
                    if len(unique_results) >= k:
                        break
        
        return unique_results
    
    def format_context(self, retrieved_items):
        """Format retrieved items as context for LLM."""
        context_parts = []
        
        for i, result in enumerate(retrieved_items, 1):
            item = result['item']
            name = item['item_name']
            restaurant = item.get('restaurant', 'Unknown')
            calories = item.get('calories', 'N/A')
            protein = item.get('protein_g', 'N/A')
            carbs = item.get('total_carbs_g', 'N/A')
            fat = item.get('total_fat_g', 'N/A')
            fiber = item.get('fiber_g', 'N/A')
            
            context_parts.append(
                f"{i}. {name} at {restaurant}\n"
                f"   - Calories: {calories}\n"
                f"   - Protein: {protein}g, Carbs: {carbs}g, Fat: {fat}g, Fiber: {fiber}g"
            )
        
        return "\n\n".join(context_parts)
    
    def ask(self, query, k=5, use_history=False, verbose=False):
        """Main method to get recommendations."""
        #Retrieve relevant items
        retrieved_items = self.retrieve(query, k=k)
        
        if verbose:
            print(f"\n🔍 Retrieved {len(retrieved_items)} items:")
            for result in retrieved_items:
                item = result['item']
                print(f"   - {item['item_name']} (score: {result['score']:.3f})")
        
        #Format context
        context = self.format_context(retrieved_items)
        
        #Build messages
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if use_history:
            messages.extend(self.conversation_history)
        
        messages.append({
            "role": "user",
            "content": f"Based on these Duke dining hall items:\n\n{context}\n\nUser query: {query}"
        })
        
        #Get LLM response
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        
        #Update history if needed
        if use_history:
            self.conversation_history.append({"role": "user", "content": query})
            self.conversation_history.append({"role": "assistant", "content": answer})
        
        return {
            'response': answer,
            'retrieved_items': retrieved_items
        }