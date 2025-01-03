

import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import time
from datetime import datetime
###
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

# Function to send an email with an attachment
def send_email(sender_email, receiver_email, subject, body, attachment_path, smtp_server, smtp_port, smtp_password):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # Attach the body text
    msg.attach(MIMEText(body, 'plain'))

    # Attach the file
    with open(attachment_path, 'rb') as attachment:
        part = MIMEApplication(attachment.read(), Name=os.path.basename(attachment_path))
    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
    msg.attach(part)

    # Send the email using SMTP_SSL for port 465
    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    server.login(sender_email, smtp_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()


###
# Define the target URL
url = 'https://www.thecable.ng/'

# Define headers to mimic a standard browser request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
}

# Make the initial HTTP request with error handling
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    exit()

# Parse the page content
soup = BeautifulSoup(response.text, 'html.parser')

# Define the keywords for each category
risk_keywords = [
    'Rape', 'rape', 'Kidnapping', 'kidnapping', 'Terrorism', 'terrorism',
    'Assaults', 'Homicide', 'homicide', 'Cultism', 'cultism',
    'Piracy', 'piracy', 'Drowning', 'Armed Robbery', 'Fire Outbreak',
    'Unsafe Route/Violent Attacks', 'Human Trafficking', 'human trafficking',
    'Crime', 'arrested', 'nabbed', 'paraded', 'detained', 'apprehended', 'arresting',
    'remanded', 'rescued', 'crime', 'Arrest', 'arrest', 'ambush', 'Ambush',
    'Bandit', 'bandit', 'accident', 'Accident', 'fraud', 'Fraud', 'corruption',
    'Corruption', 'Organ Trafficking'
]
life_death_keywords = ['Killed', 'casualties', 'casualty', 'dies', 'death', 'kill']
state_keywords = [
    'Abuja', 'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa',
    'Benue', 'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu',
    'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi',
    'Kwara', 'Lagos', 'Nassarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo',
    'Plateau', 'Rivers', 'Sokoto', 'FCT', 'Taraba', 'Yobe', 'Zamfara'
]
case_situation_keywords = ['victims', 'victim', 'injured']

# Find all the headlines
headlines = soup.find_all('div', class_='cs-entry__inner cs-entry__content')

# Extract text from headlines, follow links, and check for keywords in full content
data = []
for headline in headlines:
    title = headline.get_text(strip=True)
    link = urljoin(url, headline.find('a')['href'])

    # Visit the link to get the full content of the article
    try:
        article_response = requests.get(link, headers=headers, verify=False)
        article_response.raise_for_status()
        article_soup = BeautifulSoup(article_response.text, 'html.parser')

        # Assuming the main content is within a specific tag/class, e.g., <div class="article-content">
        article_content = article_soup.find('div', class_='entry-content')
        content = article_content.get_text(strip=True) if article_content else ""

    except requests.exceptions.HTTPError as e:
        if article_response.status_code == 403:
            print(f"Access forbidden for {link}")
            content = "Access forbidden"
        else:
            print(f"Failed to retrieve content for {link}: {e}")
            content = ""

    # Initialize columns with 'NO'
    risk_indicator = 'NO'
    life_death = 'NO'
    state = 'NO'
    case_situation = 'NO'

    # Check for each keyword in the full content
    for keyword in risk_keywords:
        if keyword.lower() in content.lower():
            risk_indicator = keyword
            break

    for keyword in life_death_keywords:
        if keyword.lower() in content.lower():
            life_death = keyword
            break

    for keyword in state_keywords:
        if keyword.lower() in content.lower():
            state = keyword
            break

    for keyword in case_situation_keywords:
        if keyword.lower() in content.lower():
            case_situation = keyword
            break

    # Add the row to the data list
    data.append({
        'title': title,
        'link': link,
        'Risk Indicator': risk_indicator,
        'Life/Death': life_death,
        'States': state,
        'Case Situation': case_situation
    })

    # Pause between requests to avoid overwhelming the server
    time.sleep(3)

# Store data in a DataFrame
df = pd.DataFrame(data)

# Combine all filtering conditions into one logical block
filter_condition = ~(
    (df['Risk Indicator'] == 'NO') &
    (df['Life/Death'] == 'NO') &
    (df['Case Situation'] == 'NO')  # Ensure rows with NO in all these columns are removed
)

# Apply the filter to exclude rows where all three columns are 'NO'
df_filtered = df[filter_condition]

# Apply a secondary filter to exclude rows where 'States' is 'NO'
df_filtered = df_filtered[df_filtered['States'] != 'NO']

# Reset the index after filtering
df_filtered.reset_index(drop=True, inplace=True)

# Save the filtered data to a CSV file with a timestamp to avoid overwriting
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
filename = f'filtered_news_headlines_{timestamp}.csv'
df_filtered.to_csv(filename, index=False)

####
# Email configuration
sender_email = os.environ.get('USER_EMAIL')
receiver_email = "riskcontrolservicesnig@gmail.com"
subject = "Cable TV Daily News Headlines"
body = "Please find attached the latest news headlines with categorized information."
smtp_server = "smtp.gmail.com"
smtp_port = 465  # SSL port for Gmail
smtp_password = os.environ.get('USER_PASSWORD')  # Defining actual app-specific password here

# Send the email
send_email(sender_email, receiver_email, subject, body, filename, smtp_server, smtp_port, smtp_password)

print("Scraping, categorization, and email sent successfully.")


