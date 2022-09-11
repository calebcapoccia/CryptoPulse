# This file contains the backend running proccess for CryptoPulse, which checks if there have been any updates based on the queries in the CryptoPulse database.
# To interact with Discord's API, I used code from this tutorial: https://www.youtube.com/watch?v=xh28F6f-Cds

import requests
import json
import time
from cs50 import SQL
import datetime
import yagmail

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///cryptopulse.db")

def main():
    # Continously check messages every x minutes
    x = 1
    while (True):
        # Get information about all queries
        queryInfo = db.execute("SELECT * FROM queries")
        
        # Create a list of dictionaries, where each dictionary represents the relevant information for each of the queries
        queries = []
        for query in range(len(queryInfo)):
            # Get the user's authorization token to access the necessary channel
            token = db.execute("SELECT token FROM users WHERE id=?", queryInfo[query]["user_id"])

            # Add dictionary with information for the necessary authorization token, channel id, keyword, server name, and channel name to the list
            queries.append({"authorization": token[0]["token"], "channel_id": queryInfo[query]["channel_id"], "keyword": queryInfo[query]["keyword"], 
                "server": queryInfo[query]["server"], "channel": queryInfo[query]["channel"]})

        # Create a list of lists for actual updates found via the Discord queries, where each item in the sublist is a dictionary with the update
        # message information
        queriesResponse = []

        # Find the timeframe to be searching for updates in
        currentTime = datetime.datetime.utcnow()
        timeframe = currentTime - datetime.timedelta(minutes=x)

        # Check messages for updates using all of the queries and the check_messages() function
        for query in range(len(queries)):
            # Returns list of updates information. If there are no updates, the list will be empty.
            queriesResponse.append(check_messages(queries[query], timeframe))
        
        # Alert the relevant user of an update if queryResponse is not empty for a query
        for query in range(len(queriesResponse)):
            if (len(queriesResponse[query]) > 0):
                # Ensure that an error did not occurr for this query
                if queriesResponse[query][0] == "ERROR":
                    # Alert the user that an error occurred for this update query.
                    themessage = f"An error occurred when checking for your update query looking for \"{queries[query]['keyword']}\" on the \
                        {queries[query]['channel']} channel of {queries[query]['server']}. Make sure you still have access to this Discord Channel or \
                        delete the query."
                    email = db.execute("SELECT email FROM users WHERE id=?", queryInfo[query]["user_id"])
                    email = email[0]["email"]
                    send_message(themessage, email)
             
                # If an update was found, send an email
                else:
                    for data in queriesResponse[query]:
                        # Construct message to send using the update query and content information
                        themessage = f"For your update query looking for \"{queries[query]['keyword']}\" on the {queries[query]['channel']} channel of \
                            {queries[query]['server']}, we found that {data['author']} wrote \"{data['content']}\" on {data['time']}."
                        
                        # Send email to the user's email
                        email = db.execute("SELECT email FROM users WHERE id=?", queryInfo[query]["user_id"])
                        email = email[0]["email"]
                        send_message(themessage, email)
        
        # Clear lists before checking again
        queries.clear()
        queriesResponse.clear()
        
        # Wait x minutes before checking again
        time.sleep(x * 60)

# The check_messages function receives query information and a timeframe to look for that query in
# Some of the code is from https://www.youtube.com/watch?v=xh28F6f-Cds
def check_messages(query, timeframe):
    # Set up authorization token for request
    headers = {
        'authorization': query["authorization"]
    }

    channel_id = query["channel_id"]
    keyword = query["keyword"]

    # Connect to Discord's API
    try:
        r = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers)
    except:
        # If an error occurred, return that an error has occurred
        return ["ERROR"]
    
    # Retrieve list of all messages
    jsonObject = json.loads(r.text)

    # Make sure information actually loaded
    r = str(r)
    if r != "<Response [200]>":
            # If not, return that an error has occurred
            return ["ERROR"]

    # Swap order of items so in chronological order
    jsonObject.reverse()

    # Create list of dictionaries to store information for each query
    foundInfo = []

    # For each message, check for pertinent information
    for message in jsonObject:
        # Retrieve the content
        content = message["content"]
        
        # Retrieve content's time and convert it to proper format
        contentTime = message["timestamp"]
        contentTime = datetime.datetime.strptime(contentTime, "%Y-%m-%dT%H:%M:%S.%f%z")
        contentTime = contentTime.replace(tzinfo=None)

        # If content is found (case insensitive) and within the timeframe, add the information the list
        if (keyword.lower() in content.lower()) and (contentTime > timeframe):
            information = {
                "author": message["author"]["username"],
                "content": message["content"],
                "time": str(contentTime)
            }
            foundInfo.append(information)

    # Return any relevant messages
    return foundInfo

# The send_message function receives a message and a user's email address and sends that message in an email to the email address
def send_message(message, email):
    # Configure yagmail to use CryptoPulse's Gmail accout
    yag = yagmail.SMTP('cryptopulse.updates@gmail.com', 'cs50finalproject')

    # Send email
    yag.send(email, 'CryptoPulse Update', message)