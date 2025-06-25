import requests
import json
from datetime import date, datetime
import xml.etree.ElementTree as ET # Import for XML parsing
import sys # Import sys for stderr printing
from bs4 import BeautifulSoup # Import BeautifulSoup for HTML parsing
import os # Import os module to access environment variables
import random # Import for selecting random items

# --- Configuration ---
# These settings will first try to read from environment variables.
# If environment variables are not set, these default values will be used.

# General Debugging
# Set to 'True' to enable debug logging. Outputs detailed information to standard output.
# Environment variable: DEBUG (expects 'True' or 'False')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# News Output Options
# Number of news items to output.
# Environment variable: NUM_NEWS_ITEMS (expects an integer)
NUM_NEWS_ITEMS = int(os.getenv('NUM_NEWS_ITEMS', '10')) # Default to 10 news items

# News Article Preview Options
# Set to 'True' to fetch and include the story preview. Set to 'False' to only show "Read more" links.
# Environment variable: SHOW_FULL_STORY_PREVIEW (expects 'True' or 'False')
SHOW_FULL_STORY_PREVIEW = os.getenv('SHOW_FULL_STORY_PREVIEW', 'False').lower() == 'true'

# Number of paragraphs to include in the story preview if SHOW_FULL_STORY_PREVIEW is True.
# Environment variable: SHOW_FULL_STORY_PARAGRAPHS (expects an integer)
SHOW_FULL_STORY_PARAGRAPHS = int(os.getenv('SHOW_FULL_STORY_PARAGRAPHS', '2'))

# Set to 'True' to display the "[Continue reading at link]" text after the preview.
# Set to 'False' to omit this link.
# Environment variable: SHOW_CONTINUE_LINK (expects 'True' or 'False')
SHOW_CONTINUE_LINK = os.getenv('SHOW_CONTINUE_LINK', 'True').lower() == 'true'

# Conversational Mode for TTS
# Set to 'True' for more conversational output, suitable for Text-to-Speech.
# Environment variable: CONVERSATIONAL_MODE (expects 'True' or 'False')
CONVERSATIONAL_MODE = os.getenv('CONVERSATIONAL_MODE', 'False').lower() == 'true'


# API Keys (prioritize environment variables)
# IMPORTANT: Replace 'YOUR_OPENWEATHERMAP_API_KEY' with your actual OpenWeatherMap API key.
# Environment variable: OPENWEATHERMAP_API_KEY
OPENWEATHERMAP_API_KEY_DEFAULT = 'YOUR_OPENWEATHERMAP_API_KEY'

# Feature Toggles
# Set to 'True' to include a random fact in the briefing.
# Environment variable: ENABLE_RANDOM_FACT (expects 'True' or 'False')
ENABLE_RANDOM_FACT = os.getenv('ENABLE_RANDOM_FACT', 'False').lower() == 'true'

# Set to 'True' to include a random joke in the briefing.
# Environment variable: ENABLE_RANDOM_JOKE (expects 'True' or 'False')
ENABLE_RANDOM_JOKE = os.getenv('ENABLE_RANDOM_JOKE', 'False').lower() == 'true'

# Set to 'True' to include an "On this day in history" event in the briefing.
# Environment variable: ENABLE_ONTHISDAY (expects 'True' or 'False')
ENABLE_ONTHISDAY = os.getenv('ENABLE_ONTHISDAY', 'False').lower() == 'true'

# Custom Location via Environment Variables
# If all three of these environment variables are set, they will override command-line location.
# Environment variables: LOCATION_NAME, LOCATION_LATITUDE, LOCATION_LONGITUDE
CUSTOM_LOCATION_NAME = os.getenv('LOCATION_NAME')
CUSTOM_LOCATION_LATITUDE = os.getenv('LOCATION_LATITUDE')
CUSTOM_LOCATION_LONGITUDE = os.getenv('LOCATION_LONGITUDE')


# RSS feed URLs (direct RSS feed URLs)
RSS_FEEDS = [
    {'url': 'https://feeds.bbci.co.uk/news/rss.xml', 'source': 'BBC News'},
    {'url': 'https://feeds.bbci.co.uk/news/england/rss.xml', 'source': 'BBC England'},
    {'url': 'https://feeds.bbci.co.uk/news/world/rss.xml', 'source': 'BBC World'},
    {'url': 'https://feeds.bbci.co.uk/news/england/essex/rss.xml', 'source': 'BBC Essex'},
    {'url': 'https://feeds.skynews.com/feeds/rss/home.xml', 'source': 'Sky News'},
    {'url': 'https://feeds.skynews.com/feeds/rss/uk.xml', 'source': 'Sky News UK'},
    {'url': 'https://feeds.skynews.com/feeds/rss/world.xml', 'source': 'Sky News World'}
]

# Coordinates for locations (Latitude, Longitude)
LOCATIONS = {
    'halstead': {'lat': 51.9451, 'lon': 0.6411, 'name': 'Halstead, Essex'},
    'braintree': {'lat': 51.878, 'lon': 0.550, 'name': 'Braintree, Essex'},
    'london': {'lat': 51.5074, 'lon': -0.1278, 'name': 'London'},
    'birmingham': {'lat': 52.4862, 'lon': -1.8904, 'name': 'Birmingham'},
    'manchester': {'lat': 53.4808, 'lon': -2.2426, 'name': 'Manchester'},
    'liverpool': {'lat': 53.4084, 'lon': -2.9916, 'name': 'Liverpool'}
}

# --- Functions ---

def get_article_preview(article_url, num_paragraphs=2):
    """
    Fetches the content of an article URL and extracts the first N substantial paragraphs.
    Returns the concatenated paragraphs or an empty string if not found/error.
    num_paragraphs: The desired number of paragraphs to extract.
    """
    if DEBUG:
        print(f"DEBUG: Fetching article preview from: {article_url}", file=sys.stdout)
    try:
        response = requests.get(article_url, timeout=5) # Shorter timeout for article fetch
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')

        paragraphs_content = []

        # List of potential selectors for main article content containers, ordered by commonality/specificity
        content_selectors = [
            {'name': 'div', 'attrs': {'class': 'sdc-article-body'}}, # Common for BBC and some Sky
            {'name': 'div', 'attrs': {'class': 'story-body__inner'}}, # Older BBC
            {'name': 'div', 'attrs': {'class': 'article__content'}},  # Often used by Sky News
            {'name': 'div', 'attrs': {'class': 'article-body'}},      # Generic but common
            {'name': 'article'}, # HTML5 semantic tag for main article content
            {'name': 'main'},    # HTML5 semantic tag for main content of the <body>
        ]

        target_container = None
        for selector in content_selectors:
            # Attempt to find the container using its tag name and attributes
            if 'attrs' in selector:
                target_container = soup.find(selector['name'], **selector['attrs'])
            else:
                target_container = soup.find(selector['name'])
            
            if target_container:
                # If a suitable container is found, break and use this one
                break 
        
        # Determine where to search for paragraphs
        if target_container:
            # If a specific container was found, search within it
            all_p_tags = target_container.find_all('p')
        else:
            # Fallback: if no specific container is found, search all paragraphs on the page
            # This is less ideal as it might pick up irrelevant text.
            all_p_tags = soup.find_all('p')

        for p_tag in all_p_tags:
            text = p_tag.get_text(strip=True)
            # Filter out very short paragraphs (e.g., image captions, single words, navigation)
            # A heuristic of > 100 characters helps ensure meaningful content.
            # Also, avoid paragraphs found within common non-article elements like headers or footers.
            if text and len(text) > 100 and not p_tag.find_parent('header') and not p_tag.find_parent('footer') and not p_tag.find_parent('nav'):
                paragraphs_content.append(text)
                if len(paragraphs_content) >= num_paragraphs:
                    break # Stop once we have enough substantial paragraphs

        return "\n\n".join(paragraphs_content[:num_paragraphs]) if paragraphs_content else "" # Return only the first N found

    except requests.exceptions.RequestException as e:
        print(f"Error fetching article content from {article_url}: {e}", file=sys.stderr)
        return ""
    except Exception as e: # Catch any other parsing errors (e.g., BeautifulSoup issues)
        print(f"Error parsing article content from {article_url}: {e}", file=sys.stderr)
        return ""


def fetch_news(feed_url, source_name):
    """
    Fetches news directly from a given RSS feed URL and extracts news items.
    Parses XML response and optionally fetches article preview.
    """
    if DEBUG:
        print(f"DEBUG: Fetching RSS from: {feed_url}", file=sys.stdout)
    news_items = []
    try:
        response = requests.get(feed_url, timeout=10) # Add timeout for robustness
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        # Parse the XML content
        root = ET.fromstring(response.content)

        # RSS feeds typically have a <channel> element containing <item> elements
        # Some might have <feed> for Atom, but common RSS uses <channel>
        channel = root.find('channel')
        if channel is None:
            # Try to find feed for Atom feeds, if it's not a standard RSS channel
            feed = root.find('{http://www.w3.org/2005/Atom}feed')
            if feed is not None:
                # Handle Atom feed structure if necessary, for now, assume RSS
                if DEBUG:
                    print(f"DEBUG: Found Atom feed structure for {source_name}. Parsing as RSS might be incomplete.", file=sys.stdout)
                items_elements = feed.findall('{http://www.w3.org/2005/Atom}entry')
            else:
                print(f"Warning: No 'channel' or 'feed' element found in XML response from {source_name}.", file=sys.stderr)
                return []
        else:
            items_elements = channel.findall('item')
        
        if not items_elements:
            print(f"Warning: No 'item' elements found in response from {source_name}. URL: {feed_url}", file=sys.stderr)
            return []

        # Take top items (more than NUM_NEWS_ITEMS to allow for deduplication)
        # We fetch up to 2 * NUM_NEWS_ITEMS from each source to increase chances of getting enough unique ones
        # after deduplication, but the final limit is applied later.
        fetch_limit_per_source = max(NUM_NEWS_ITEMS, 10) * 2 # Ensure at least 10 or 2x the requested number per source
        for item_element in items_elements[:fetch_limit_per_source]:
            title = item_element.find('title')
            description = item_element.find('description')
            link = item_element.find('link')
            
            item_link = link.text.strip() if link is not None and link.text else '#'

            news_item = {
                'title': title.text.strip() if title is not None and title.text else 'No Title',
                'description': description.text.strip() if description is not None and description.text else 'No Description',
                'link': item_link,
                'source': source_name
            }
            
            # Fetch full story preview if enabled
            if SHOW_FULL_STORY_PREVIEW and item_link and item_link != '#':
                news_item['full_story_preview'] = get_article_preview(item_link, num_paragraphs=SHOW_FULL_STORY_PARAGRAPHS)
            else:
                news_item['full_story_preview'] = "" # Ensure the key exists even if empty

            news_items.append(news_item)
        return news_items
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news from {source_name} ({feed_url}): {e}", file=sys.stderr)
        return []
    except ET.ParseError as e:
        print(f"Error parsing XML from {source_name} ({feed_url}): {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred while processing news from {source_name} ({feed_url}): {e}", file=sys.stderr)
        return []


def deduplicate_news(all_news):
    """
    Deduplicates news headlines based on title and description to avoid repetition.
    """
    unique_news = []
    seen_identifiers = set() # Use a set to store unique identifiers

    for item in all_news:
        # Create a unique identifier from a combination of title and description
        identifier = (item['title'].lower().strip(), item['description'].lower().strip())
        if identifier not in seen_identifiers:
            unique_news.append(item)
            seen_identifiers.add(identifier)
    return unique_news

def fetch_weather(lat, lon, api_key):
    """
    Fetches daily weather forecast from OpenWeatherMap One Call API 3.0.
    """
    # OpenWeatherMap One Call API 3.0 URL
    weather_api_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts&units=metric&appid={api_key}"
    if DEBUG:
        print(f"DEBUG: Fetching weather from: {weather_api_url}", file=sys.stdout)
    try:
        response = requests.get(weather_api_url, timeout=10) # Add timeout
        response.raise_for_status() # Raise an HTTPError for bad responses
        data = response.json()

        if 'daily' not in data or not data['daily']:
            print(f"Warning: 'daily' weather data not found for lat={lat}, lon={lon}. Data: {data}", file=sys.stderr)
            return None

        today = data['daily'][0] # Get today's forecast
        return {
            'description': today['weather'][0]['description'],
            'max_temp': today['temp']['max'],
            'min_temp': today['temp']['min'],
            'feels_like': today['feels_like']['day']
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from weather API: {e}", file=sys.stderr)
        return None
    except KeyError as e:
        print(f"Error parsing weather data (missing key: {e}): {data}", file=sys.stderr)
        return None

def fetch_random_fact():
    """
    Fetches a random fact from the Useless Facts API.
    Returns the fact text or None on error.
    """
    fact_api_url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
    if DEBUG:
        print(f"DEBUG: Fetching random fact from: {fact_api_url}", file=sys.stdout)
    try:
        response = requests.get(fact_api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and data.get('text'):
            return data['text']
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching random fact: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from fact API: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching/parsing random fact: {e}", file=sys.stderr)
        return None

def fetch_random_joke():
    """
    Fetches a random joke from JokeAPI.
    Returns the joke text or None on error.
    """
    # Using 'Any' category with blacklisted flags for appropriate content
    joke_api_url = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=racist,sexist,explicit&type=single"
    if DEBUG:
        print(f"DEBUG: Fetching random joke from: {joke_api_url}", file=sys.stdout)
    try:
        response = requests.get(joke_api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and data.get('joke'):
            return data['joke']
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching random joke: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from joke API: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching/parsing random joke: {e}", file=sys.stderr)
        return None

def fetch_on_this_day_event():
    """
    Fetches a random "On this day in history" event for the current date.
    Uses byabbe.se API which sources from Wikipedia.
    Returns the event text or None on error.
    """
    today_date = date.today()
    month = today_date.month
    day = today_date.day
    onthisday_api_url = f"https://byabbe.se/on-this-day/{month}/{day}/events.json"
    if DEBUG:
        print(f"DEBUG: Fetching 'On this day' event from: {onthisday_api_url}", file=sys.stdout)
    try:
        response = requests.get(onthisday_api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('events') and len(data['events']) > 0:
            # Pick a random event from the list to keep it varied
            # The 'text' field contains the event description
            # Filter out events with no year or description
            valid_events = [e for e in data['events'] if e.get('year') and e.get('description')]
            if valid_events:
                random_event = random.choice(valid_events)
                return f"{random_event.get('year')}: {random_event.get('description')}"
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching 'On this day' event: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from 'On this day' API: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching/parsing 'On this day' event: {e}", file=sys.stderr)
        return None


def get_time_based_greeting():
    """Returns 'Good morning', 'Good afternoon', or 'Good evening' based on current time."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"


def format_briefing(weather_data, news_items, random_fact, random_joke, onthisday_event, location_name):
    """
    Formats the weather, news, random fact, random joke, and 'On this day' data into a readable daily briefing string.
    Applies conversational mode if CONVERSATIONAL_MODE is True.
    """
    briefing_parts = []
    today_formatted = date.today().strftime('%A, %d %B %Y')

    if CONVERSATIONAL_MODE:
        briefing_parts.append(f"{get_time_based_greeting()}! This is your daily briefing for {today_formatted}.")
        briefing_parts.append("") # Add a blank line for spacing
    else:
        briefing_parts.append(f"# Daily Briefing - {today_formatted}")
        briefing_parts.append("") # Add a blank line for spacing

    # Weather Section
    if CONVERSATIONAL_MODE:
        briefing_parts.append(f"Here's the weather for {location_name}:")
    else:
        briefing_parts.append(f"## Weather for {location_name}")
    
    if weather_data:
        briefing_parts.append(f"Today's forecast: {weather_data['description'].capitalize()}")
        briefing_parts.append(f"The maximum temperature expected is {round(weather_data['max_temp'])}°C, with a minimum of {round(weather_data['min_temp'])}°C.")
        briefing_parts.append(f"It will feel like {round(weather_data['feels_like'])}°C.")
        briefing_parts.append("")
    else:
        briefing_parts.append("Weather forecast currently unavailable.")
        briefing_parts.append("")

    # News Section
    if CONVERSATIONAL_MODE:
        briefing_parts.append(f"The top news headlines for you are:")
    else:
        briefing_parts.append("## Top News Headlines")
    briefing_parts.append("")

    if news_items:
        for i, item in enumerate(news_items):
            if CONVERSATIONAL_MODE:
                briefing_parts.append(f"Headline number {i + 1} from {item['source']}: {item['title']}.")
                briefing_parts.append(f"Summary: {item['description']}.")
                if SHOW_FULL_STORY_PREVIEW and item.get('full_story_preview'):
                    briefing_parts.append(f"Here's a preview of the story:")
                    briefing_parts.append(f"{item['full_story_preview']}")
                    if SHOW_CONTINUE_LINK:
                        briefing_parts.append(f"You can continue reading more at the link: {item['link']}")
                briefing_parts.append("") # Add a blank line after each news item
            else:
                briefing_parts.append(f"### {i + 1}. {item['title']} ({item['source']})")
                briefing_parts.append(f"{item['description']}")
                if SHOW_FULL_STORY_PREVIEW and item.get('full_story_preview'):
                    briefing_parts.append(f"{item['full_story_preview']}")
                    if SHOW_CONTINUE_LINK:
                        briefing_parts.append(f"[Continue reading at {item['link']}]")
                briefing_parts.append("")
    else:
        briefing_parts.append("No news headlines available.")
        briefing_parts.append("")

    # Random Fact Section
    if ENABLE_RANDOM_FACT:
        if CONVERSATIONAL_MODE:
            briefing_parts.append("Did you know this fact?")
        else:
            briefing_parts.append("## Fact of the Day")
        if random_fact:
            briefing_parts.append(random_fact)
            briefing_parts.append("")
        else:
            briefing_parts.append("Fact of the day currently unavailable.")
            briefing_parts.append("")
    
    # Random Joke Section
    if ENABLE_RANDOM_JOKE:
        if CONVERSATIONAL_MODE:
            briefing_parts.append("Here's a joke to start your day:")
        else:
            briefing_parts.append("## Joke of the Day")
        if random_joke:
            briefing_parts.append(random_joke)
            briefing_parts.append("")
        else:
            briefing_parts.append("Joke of the day currently unavailable.")
            briefing_parts.append("")

    # On This Day Section
    if ENABLE_ONTHISDAY:
        if CONVERSATIONAL_MODE:
            briefing_parts.append("And finally, on this day in history:")
        else:
            briefing_parts.append("## On This Day in History")
        if onthisday_event:
            briefing_parts.append(onthisday_event)
            briefing_parts.append("")
        else:
            briefing_parts.append("On this day in history currently unavailable.")
            briefing_parts.append("")

    return "\n".join(briefing_parts)

# --- Main Execution ---
if __name__ == "__main__":
    selected_location = {} # Initialize selected_location dictionary

    # Check for custom location environment variables first
    if CUSTOM_LOCATION_NAME and CUSTOM_LOCATION_LATITUDE and CUSTOM_LOCATION_LONGITUDE:
        try:
            selected_location['name'] = CUSTOM_LOCATION_NAME
            selected_location['lat'] = float(CUSTOM_LOCATION_LATITUDE)
            selected_location['lon'] = float(CUSTOM_LOCATION_LONGITUDE)
            if DEBUG:
                print(f"DEBUG: Using custom location from environment variables: {selected_location['name']} ({selected_location['lat']}, {selected_location['lon']})", file=sys.stdout)
        except ValueError:
            print("Error: Invalid numeric values for LOCATION_LATITUDE or LOCATION_LONGITUDE environment variables.", file=sys.stderr)
            sys.exit(1)
    else:
        # Fallback to command-line argument if custom env vars are not fully set
        if CUSTOM_LOCATION_NAME or CUSTOM_LOCATION_LATITUDE or CUSTOM_LOCATION_LONGITUDE:
            print("Warning: Partial custom location environment variables set. Please set LOCATION_NAME, LOCATION_LATITUDE, and LOCATION_LONGITUDE together, or none of them.", file=sys.stderr)

        # Get location from first command line argument, default to 'halstead'
        selected_location_key = sys.argv[1].lower() if len(sys.argv) > 1 else 'halstead'
        
        if selected_location_key not in LOCATIONS:
            print(f"Error: Invalid location specified via command line. Choose from {list(LOCATIONS.keys())}", file=sys.stderr)
            sys.exit(1)
        selected_location = LOCATIONS[selected_location_key]


    # API Key Handling
    owm_api_key = os.getenv('OPENWEATHERMAP_API_KEY', OPENWEATHERMAP_API_KEY_DEFAULT)
    
    if owm_api_key == OPENWEATHERMAP_API_KEY_DEFAULT or not owm_api_key:
        print("Error: OpenWeatherMap API key is not set. Please set the OPENWEATHERMAP_API_KEY environment variable or replace the placeholder in the script.", file=sys.stderr)
        sys.exit(1)
    
    if DEBUG:
        print("--- DEBUG Configuration ---", file=sys.stdout)
        print(f"DEBUG (env): {os.getenv('DEBUG')}, Script Value: {DEBUG}", file=sys.stdout)
        print(f"NUM_NEWS_ITEMS (env): {os.getenv('NUM_NEWS_ITEMS')}, Script Value: {NUM_NEWS_ITEMS}", file=sys.stdout)
        print(f"SHOW_FULL_STORY_PREVIEW (env): {os.getenv('SHOW_FULL_STORY_PREVIEW')}, Script Value: {SHOW_FULL_STORY_PREVIEW}", file=sys.stdout)
        print(f"SHOW_FULL_STORY_PARAGRAPHS (env): {os.getenv('SHOW_FULL_STORY_PARAGRAPHS')}, Script Value: {SHOW_FULL_STORY_PARAGRAPHS}", file=sys.stdout)
        print(f"SHOW_CONTINUE_LINK (env): {os.getenv('SHOW_CONTINUE_LINK')}, Script Value: {SHOW_CONTINUE_LINK}", file=sys.stdout)
        print(f"CONVERSATIONAL_MODE (env): {os.getenv('CONVERSATIONAL_MODE')}, Script Value: {CONVERSATIONAL_MODE}", file=sys.stdout)
        print(f"ENABLE_RANDOM_FACT (env): {os.getenv('ENABLE_RANDOM_FACT')}, Script Value: {ENABLE_RANDOM_FACT}", file=sys.stdout)
        print(f"ENABLE_RANDOM_JOKE (env): {os.getenv('ENABLE_RANDOM_JOKE')}, Script Value: {ENABLE_RANDOM_JOKE}", file=sys.stdout)
        print(f"ENABLE_ONTHISDAY (env): {os.getenv('ENABLE_ONTHISDAY')}, Script Value: {ENABLE_ONTHISDAY}", file=sys.stdout)
        
        print(f"OPENWEATHERMAP_API_KEY (env): {'***SET***' if os.getenv('OPENWEATHERMAP_API_KEY') else 'NOT SET'}, Script Value set: {bool(owm_api_key) and owm_api_key != OPENWEATHERMAP_API_KEY_DEFAULT}", file=sys.stdout)
        # Custom location debug print
        print(f"LOCATION_NAME (env): {CUSTOM_LOCATION_NAME}, LOCATION_LATITUDE (env): {CUSTOM_LOCATION_LATITUDE}, LOCATION_LONGITUDE (env): {CUSTOM_LOCATION_LONGITUDE}", file=sys.stdout)
        print("---------------------------", file=sys.stdout)


    # Fetch all news concurrently
    all_news_promises = [fetch_news(feed['url'], feed['source']) for feed in RSS_FEEDS]
    
    # Execute all news fetching requests
    all_news_results = []
    for promise in all_news_promises:
        all_news_results.extend(promise)

    flat_news = all_news_results
    unique_news = deduplicate_news(flat_news)
    
    # --- Apply NUM_NEWS_ITEMS limit to the final unique news list ---
    final_news_items = unique_news[:NUM_NEWS_ITEMS]

    # Fetch weather
    weather_data = fetch_weather(selected_location['lat'], selected_location['lon'], owm_api_key)

    # Fetch random fact (conditionally)
    random_fact = None
    if ENABLE_RANDOM_FACT:
        random_fact = fetch_random_fact()
    
    # Fetch random joke (conditionally)
    random_joke = None
    if ENABLE_RANDOM_JOKE:
        random_joke = fetch_random_joke()

    # Fetch 'On this day' event (conditionally)
    onthisday_event = None
    if ENABLE_ONTHISDAY:
        onthisday_event = fetch_on_this_day_event()


    # Generate and print briefing
    briefing_text = format_briefing(weather_data, final_news_items, random_fact, random_joke, onthisday_event, selected_location['name'])
    print(briefing_text)
