import os
from openai import OpenAI
import pandas as pd
import urllib.parse, feedparser
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
    data.append({'Publication Date': pub_date, 'Title': title, 'Link':entry.link})

# Create a pandas DataFrame
df = pd.DataFrame(data)

question = "What is the overall sentiment? Provide a sentiment score between -1 to 1 and elaborate your reasons" # @param ["What is the overall sentiment? Provide a sentiment score between -1 to 1 and elaborate your reasons", "You are an investment analyst, write some long term investment advice", "You are a momentum trader, provide some short term trading ideas"] {allow-input: true}
questionWithContext = question + "  Use the following context: \n\n" + all_headlines

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful financial expert, you do not answer questions unrelated to finance."},
        {"role": "user", "content": questionWithContext},
    ],
    stream=False
)

print(response.choices[0].message.content)
display(df)
