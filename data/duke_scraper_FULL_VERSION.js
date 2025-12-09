// DUKE DINING COMPLETE SCRAPER - ALL FORMATS SUPPORTED
// =====================================================
// Handles: Direct items, Breakfast/Lunch/Dinner, All Day, Specialty Drinks,
// Combo Meal Menu, Smoothies, Late Night, All Day Service, etc.
//
// INSTRUCTIONS:
// 1. Go to https://netnutrition.cbord.com/nn-prod/Duke
// 2. Press F12 (Developer Tools)
// 3. Go to "Console" tab
// 4. Paste this ENTIRE script
// 5. Press Enter
// 6. Wait 15-30 minutes
// 7. CSV will auto-download

console.log('🍽️  DUKE DINING COMPLETE SCRAPER');
console.log('=================================\n');

const CONFIG = {
    delayBetweenClicks: 700,
    delayAfterExpand: 400,
    delayAfterRestaurant: 1500,
};

// FULL VERSION - All restaurants
const TEST_MODE = false;
const MAX_TEST_ITEMS = 3;

const RESTAURANTS = [
    { name: "Bella Union", unitOid: 6 },
    { name: "Beyu Blue Coffee", unitOid: 24 },
    { name: "Bseisu Coffee Bar", unitOid: 10 },
    { name: "Cafe", unitOid: 14 },
    { name: "Duke Marine Lab", unitOid: 2 },
    { name: "Freeman Café", unitOid: 3 },
    { name: "Ginger + Soy", unitOid: 22 },
    { name: "Gothic Grill", unitOid: 25 },
    { name: "Gyotaku", unitOid: 23 },
    { name: "Il Forno", unitOid: 20 },
    { name: "It's Thyme", unitOid: 27 },
    { name: "J.B.'s Roast & Chops", unitOid: 7 },
    { name: "Marketplace", unitOid: 4 },
    { name: "Nasher Museum Café", unitOid: 17 },
    { name: "Red Mango", unitOid: 18 },
    { name: "Saladalia @ The Perk", unitOid: 15 },
    { name: "Sanford Deli", unitOid: 16 },
    { name: "Sazon", unitOid: 21 },
    { name: "Sprout", unitOid: 11 },
    { name: "Tandoor Indian Cuisine", unitOid: 19 },
    { name: "The Devils Krafthouse", unitOid: 26 },
    { name: "The Farmstead", unitOid: 12 },
    { name: "The Pitchfork", unitOid: 8 },
    { name: "The Skillet", unitOid: 9 },
    { name: "Trinity Cafe", unitOid: 5 },
    { name: "Twinnie's", unitOid: 13 },
    { name: "Zweli's Café at Duke Divinity", unitOid: 28 }
];

// All possible meal period keywords
const MEAL_PERIOD_KEYWORDS = [
    'Breakfast',
    'Lunch',
    'Dinner',
    'Brunch',
    'All Day',
    'Specialty Drinks',
    'Combo Meal Menu',
    'Smoothies',
    'Lunch/Dinner',
    'Lunch and Dinner',
    'Lunch & Dinner',
    'Late Night',
    'All Day Service'
];

const allData = [];
let totalItemsScraped = 0;

const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ===================================================================
// MAIN SCRAPING LOGIC
// ===================================================================

async function scrapeAllRestaurants() {
    console.log(`📋 Starting scrape of ${RESTAURANTS.length} restaurants...\n`);
    
    for (let i = 0; i < RESTAURANTS.length; i++) {
        const restaurant = RESTAURANTS[i];
        console.log(`${'='.repeat(70)}`);
        console.log(`📍 [${i + 1}/${RESTAURANTS.length}] ${restaurant.name}`);
        console.log(`${'='.repeat(70)}`);
        
        try {
            await scrapeRestaurant(restaurant);
        } catch (error) {
            console.error(`❌ Error scraping ${restaurant.name}:`, error);
        }
        
        await wait(CONFIG.delayAfterRestaurant);
    }
    
    console.log('\n' + '='.repeat(70));
    console.log(`✅ SCRAPING COMPLETE!`);
    console.log(`📊 Total items scraped: ${totalItemsScraped}`);
    console.log('='.repeat(70));
    
    downloadCSV(allData);
}

async function scrapeRestaurant(restaurant) {
    // Find and click the restaurant
    const restaurantLink = findRestaurantLink(restaurant.name);
    
    if (!restaurantLink) {
        console.warn(`⚠️  Could not find link for ${restaurant.name}`);
        return;
    }
    
    restaurantLink.click();
    await wait(CONFIG.delayAfterRestaurant);
    
    // Detect structure: meal periods or direct items
    const mealPeriods = findMealPeriods();
    
    if (mealPeriods.length > 0) {
        console.log(`   Found ${mealPeriods.length} meal periods: ${mealPeriods.map(p => p.name).join(', ')}`);
        
        for (const period of mealPeriods) {
            console.log(`\n   ⏰ ${period.name}`);
            period.element.click();
            await wait(CONFIG.delayBetweenClicks);
            
            await scrapeCurrentPage(restaurant.name, period.name);
        }
    } else {
        // No meal periods, scrape directly
        console.log(`   No meal periods found, scraping all items...`);
        await scrapeCurrentPage(restaurant.name, 'All Day');
    }
}

async function scrapeCurrentPage(restaurantName, mealPeriod) {
    // Expand all dropdowns/categories
    await expandAllCategories();
    
    // Find all item rows
    const itemRows = findAllItemRows();
    console.log(`      Found ${itemRows.length} items`);
    
    // In test mode, only do first 3 items
    const maxItems = TEST_MODE ? Math.min(MAX_TEST_ITEMS, itemRows.length) : itemRows.length;
    
    for (let i = 0; i < maxItems; i++) {
        const row = itemRows[i];
        try {
            const itemData = await scrapeItemRow(row, restaurantName, mealPeriod);
            if (itemData) {
                allData.push(itemData);
                totalItemsScraped++;
                const displayName = itemData.item_name.substring(0, 45);
                console.log(`      ✓ [${i + 1}/${maxItems}] ${displayName}`);
            }
        } catch (error) {
            console.warn(`      ⚠️  Error on item ${i + 1}:`, error.message);
        }
        
        await wait(CONFIG.delayBetweenClicks);
    }
    
    if (TEST_MODE) {
        console.log(`      🧪 TEST MODE: Stopped after ${maxItems} items`);
    }
}

// ===================================================================
// FINDING ELEMENTS
// ===================================================================

function findRestaurantLink(name) {
    const allLinks = document.querySelectorAll('a, button, [role="button"]');
    for (const link of allLinks) {
        if (link.textContent.trim() === name && link.offsetParent !== null) {
            return link;
        }
    }
    return null;
}

function findMealPeriods() {
    const periods = [];
    const allElements = document.querySelectorAll('a, button, [role="button"]');
    
    for (const el of allElements) {
        const text = el.textContent.trim();
        
        // Check if text matches any meal period keyword
        const isMatch = MEAL_PERIOD_KEYWORDS.some(keyword => 
            text === keyword || text.includes(keyword)
        );
        
        if (isMatch && el.offsetParent !== null && text.length < 100) {
            // Avoid duplicates
            if (!periods.some(p => p.name === text)) {
                periods.push({ name: text, element: el });
            }
        }
    }
    
    return periods;
}

async function expandAllCategories() {
    // Find expandable elements
    const selectors = [
        'details:not([open])',
        'summary',
        '[class*="category"]',
        '[class*="dropdown"]'
    ];
    
    for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        for (const elem of elements) {
            const text = elem.textContent;
            if (text.includes('▸') || text.includes('►') || elem.tagName === 'SUMMARY') {
                elem.click();
                await wait(CONFIG.delayAfterExpand);
            }
        }
    }
}

function findAllItemRows() {
    const rows = [];
    const tables = document.querySelectorAll('table');
    
    for (const table of tables) {
        const tableRows = table.querySelectorAll('tr');
        for (const row of tableRows) {
            // Skip if it's a header row
            if (row.querySelector('th')) continue;
            
            // Must have cells
            const cells = row.querySelectorAll('td');
            if (cells.length === 0) continue;
            
            // Look for the item name link (this is what we click)
            const hasItemLink = row.querySelector('a[href*="#"], a.item, td a');
            if (!hasItemLink) continue;
            
            // Make sure it's not a navigation link
            const linkText = hasItemLink.textContent.trim();
            if (linkText.length < 2 || linkText === 'Back' || linkText === 'Compare Items') continue;
            
            rows.push(row);
        }
    }
    
    return rows;
}

// ===================================================================
// SCRAPING ITEM DATA
// ===================================================================

async function scrapeItemRow(row, restaurantName, mealPeriod) {
    // Get serving size first (before we mess with the row)
    const servingSize = getServingSize(row);
    
    // Get dietary labels (vegan, vegetarian, etc.)
    const dietaryLabels = getDietaryLabels(row);
    
    // Find the item name LINK (clicking this opens nutrition)
    const itemLink = row.querySelector('a[href*="#"], a.item, td a');
    
    if (!itemLink) {
        console.warn(`        No item link found in row`);
        return null;
    }
    
    const itemName = itemLink.textContent.trim();
    if (!itemName || itemName.length < 2) return null;
    
    // Click the ITEM NAME to open nutrition modal
    itemLink.click();
    await wait(CONFIG.delayBetweenClicks);
    
    // Extract nutrition data
    const nutritionData = extractNutritionFromModal();
    
    // Close modal
    await closeModal();
    
    return {
        restaurant: restaurantName,
        meal_period: mealPeriod,
        item_name: itemName,
        serving_size: servingSize,
        dietary_labels: dietaryLabels,
        ...nutritionData
    };
}

function getServingSize(row) {
    const cells = row.querySelectorAll('td');
    for (const cell of cells) {
        const text = cell.textContent.trim();
        if (text.match(/\d+\s*(oz|g|ml|cup|piece|portion|slice|each|item|serving)/i)) {
            return text;
        }
    }
    return '';
}

function getDietaryLabels(row) {
    const labels = [];
    
    // Look for images with alt text
    const imgs = row.querySelectorAll('img[alt], img[title]');
    for (const img of imgs) {
        const alt = (img.alt || img.title || '').toLowerCase();
        if (alt.includes('vegan')) labels.push('Vegan');
        else if (alt.includes('vegetarian')) labels.push('Vegetarian');
        else if (alt.includes('gluten')) labels.push('Gluten Free');
        else if (alt.includes('dairy')) labels.push('Dairy Free');
        else if (alt.includes('halal')) labels.push('Halal');
        else if (alt.includes('kosher')) labels.push('Kosher');
    }
    
    // Also check for text
    const text = row.textContent;
    const keywords = {
        'Vegan': /\bVegan\b/i,
        'Vegetarian': /\bVegetarian\b/i,
        'Gluten Free': /\bGluten Free\b/i,
        'Halal': /\bHalal\b/i
    };
    
    for (const [label, regex] of Object.entries(keywords)) {
        if (regex.test(text) && !labels.includes(label)) {
            labels.push(label);
        }
    }
    
    return labels.join('; ');
}

// ===================================================================
// NUTRITION EXTRACTION
// ===================================================================

function extractNutritionFromModal() {
    // Try multiple ways to find the visible modal
    let modal = null;
    
    // Method 1: Look for modal that's actually visible
    const modals = document.querySelectorAll('[class*="modal"], [class*="dialog"], [role="dialog"]');
    for (const m of modals) {
        // Check if it's visible and contains nutrition info
        if (m.offsetParent !== null && m.textContent.includes('Nutrition Information')) {
            modal = m;
            break;
        }
    }
    
    // Method 2: Just look for anything with "Nutritional Information" visible
    if (!modal) {
        const allElements = document.querySelectorAll('div, section');
        for (const el of allElements) {
            if (el.offsetParent !== null && 
                el.textContent.includes('Nutrition Information') && 
                el.textContent.includes('Calories')) {
                modal = el;
                break;
            }
        }
    }
    
    if (!modal) {
        console.log('        ⚠️  Could not find modal');
        return {};
    }
    
    const text = modal.textContent;
    
    // Extract calories with multiple patterns
    let calories = '';
    
    // Try pattern 1: NO SPACE between Calories and number (most common!)
    calories = extractMatch(text, /Calories(\d+)/i);
    
    // Try pattern 2: Standard format with space
    if (!calories) {
        calories = extractMatch(text, /Calories\s+(\d+)/i);
    }
    
    // Try pattern 3: With "Amount Per Serving" prefix
    if (!calories) {
        calories = extractMatch(text, /Amount Per Serving\s+Calories\s*(\d+)/i);
    }
    
    // Try pattern 4: Line breaks/whitespace between
    if (!calories) {
        const calMatch = text.match(/Calories[\s\n]*(\d+)/i);
        if (calMatch) {
            calories = calMatch[1];
        }
    }
    
    // Extract serving size - try to get the full format with grams
    let serving = extractMatch(text, /Serving Size\s+([\d.]+\s*oz\s*\([\d]+g\))/i);
    if (!serving) {
        serving = extractMatch(text, /Serving Size\s+([\d.]+\s*oz)/i);
    }
    if (!serving) {
        serving = extractMatch(text, /Serving Size\s+([^\n]+)/i);
    }
    
    const nutrition = {
        serving_size: serving,
        calories: calories,
        total_fat_g: extractMatch(text, /Total Fat\s+(\d+\.?\d*)g/i),
        saturated_fat_g: extractMatch(text, /Saturated Fat\s+(\d+\.?\d*g|NA)/i),
        trans_fat_g: extractMatch(text, /Trans Fat\s+(\d+\.?\d*g|NA)/i),
        cholesterol_mg: extractMatch(text, /Cholesterol\s+(\d+mg|NA)/i),
        sodium_mg: extractMatch(text, /Sodium\s+(\d+)mg/i),
        total_carbs_g: extractMatch(text, /Total Carbohydrate\s+(\d+\.?\d*)g/i),
        fiber_g: extractMatch(text, /Dietary Fiber\s+(<\s*\d+g|\d+\.?\d*g)/i),
        sugars_g: extractMatch(text, /Total Sugars\s+(\d+\.?\d*g)/i),
        protein_g: extractMatch(text, /Protein\s+(\d+\.?\d*)g/i),
        ingredients: extractIngredients(text)
    };
    
    return nutrition;
}

function extractMatch(text, regex) {
    const match = text.match(regex);
    return match ? match[1].trim() : '';
}

function extractIngredients(text) {
    const match = text.match(/Ingredients:\s*([^]*?)(?=\*|Contains:|Allergen|Nutrition|$)/i);
    if (match) {
        return match[1].trim().replace(/\s+/g, ' ').substring(0, 2000);
    }
    return '';
}

async function closeModal() {
    const closeSelectors = [
        'button[aria-label*="lose"]',
        'button[class*="close"]',
        'button.close',
        '[class*="modal-close"]',
        'button[title*="Close"]'
    ];
    
    for (const selector of closeSelectors) {
        const btn = document.querySelector(selector);
        if (btn && btn.offsetParent !== null) {
            btn.click();
            await wait(300);
            return;
        }
    }
    
    // Fallback: press Escape
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27 }));
    await wait(300);
}

// ===================================================================
// CSV EXPORT
// ===================================================================

function downloadCSV(data) {
    if (data.length === 0) {
        console.error('❌ No data to export!');
        return;
    }
    
    console.log('\n💾 Generating CSV...');
    
    const headers = Object.keys(data[0]);
    const csvRows = [headers.join(',')];
    
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header] || '';
            const escaped = String(value).replace(/"/g, '""');
            return `"${escaped}"`;
        });
        csvRows.push(values.join(','));
    }
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    
    link.href = url;
    link.download = `duke_dining_complete_${timestamp}.csv`;
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    console.log('✅ CSV downloaded successfully!');
}

// ===================================================================
// START
// ===================================================================

console.log('🚀 Starting in 3 seconds...');
if (TEST_MODE) {
    console.log('🧪 TEST MODE: Only scraping Bella Union (first 3 items)');
    console.log('⏱️  This should take about 30 seconds.');
} else {
    console.log('⏳ This will take 15-30 minutes.');
}
console.log('📱 Please keep this tab open and active!\n');

setTimeout(() => {
    scrapeAllRestaurants().catch(error => {
        console.error('❌ Fatal error:', error);
        if (allData.length > 0) {
            console.log('💾 Saving partial data...');
            downloadCSV(allData);
        }
    });
}, 3000);
