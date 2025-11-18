import os
from openai import OpenAI
import pandas as pd
from IPython.display import display
import urllib.parse, feedparser
import requests
from datetime import datetime, timedelta

DATE_FORMAT = '%Y-%m-%d'
today_date = (datetime.now() + timedelta(days=1)).strftime(DATE_FORMAT)
seven_days_ago = (datetime.now() - timedelta(days=7)).strftime(DATE_FORMAT)


client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

news_query = 'Cloudflare' 
startDate = seven_days_ago 
endDate = today_date 

# Specify the RSS feed URL
feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(news_query)}+after:{startDate}+before:{endDate}"
print(feed_url)

# Parse the RSS feed
feed = feedparser.parse(feed_url)

# Extract headlines and other relevant information
entries = feed.entries
all_headlines = ''

data = []
for entry in entries:
    title = entry.title
    all_headlines += title + " "
    pub_date = entry.published  # Or entry.updated
    # Resolve original article URL when RSS provides a redirect/Google wrapper
    def get_original_link(entry, follow_redirect=True, timeout=5):
        link = entry.get('link') or entry.get('id') or ''
        # check common redirect query params
        for u in (link,) + tuple(l.get('href') for l in entry.get('links', []) if l.get('href')):
            if not u:
                continue
            q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
            for key in ('url', 'u', 'q', 'qurl'):
                if q.get(key):
                    return urllib.parse.unquote(q[key][0])
        # prefer alternate/html links
        for l in entry.get('links', []):
            href = l.get('href')
            rel = (l.get('rel') or '').lower()
            typ = (l.get('type') or '').lower()
            if href and (rel in ('alternate', '') or typ.startswith('text/html')):
                return href
        # follow redirects as last resort
        if follow_redirect and link:
            try:
                r = requests.head(link, allow_redirects=True, timeout=timeout)
                if r.ok:
                    return r.url
                return requests.get(link, allow_redirects=True, timeout=timeout).url
            except Exception:
                pass
        return link

    data.append({'Publication Date': pub_date, 'Title': title, 'Link': get_original_link(entry)})

# Create a pandas DataFrame
df = pd.DataFrame(data)

question = "What is the overall sentiment? Provide a sentiment score between -1 to 1 and elaborate your reasons" # @param ["What is the overall sentiment? Provide a sentiment score between -1 to 1 and elaborate your reasons", "You are an investment analyst, write some long term investment advice", "You are a momentum trader, provide some short term trading ideas"] {allow-input: true}
#questionWithContext = question + "  Use the following context: \n\n" + all_headlines
questionWithContext = 'what is the weather today?'


response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful financial expert, you do not answer non financial questions"},
        {"role": "user", "content": questionWithContext},
    ],
    stream=False
)

print(response.choices[0].message.content)
display(df)
