import streamlit as st
from pymongo import MongoClient
import mysql.connector
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests_cache
from datetime import datetime
import re

# Initialize requests_cache
requests_cache.install_cache("youtube_cache", expire_after=3600)  # Cache expires after 1 hour

# Initialize MongoDB client
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["youtube_data"]

# Initialize MySQL connection
mysql_connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Root@7890sql",
    database="youtube_db"
)
mysql_cursor = mysql_connection.cursor()

# Google API setup
api_key = "AIzaSyCvPvy3XuQO5tN2wjZiiGhHick4OOrg-pA"
youtube_service = build("youtube", "v3", developerKey=api_key)

# Streamlit app
def main():
    st.title("YouTube Data Harvesting")
    st.write("---")

    menu = ["Retrieve YouTube Channel Data", "Migrate Data to SQL", "Search in SQL Database"]
    choice = st.sidebar.selectbox("Select an option", menu)

    if choice == "Retrieve YouTube Channel Data":
        store_data_in_mongodb()
    elif choice == "Migrate Data to SQL":
        migrate_data_to_sql()
    elif choice == "Search in SQL Database":
        search_sql_database()

# Get YouTube channel data using Google API
def get_channel_data(channel_id):
    response = youtube_service.channels().list(
        part="snippet, statistics, contentDetails",
        id=channel_id
    ).execute()

    channel_data = {}
    if response.get("items"):
        channel = response["items"][0]
        channel_data["_id"] = channel["snippet"]["title"]
        channel_data["Channel Name"] = channel["snippet"]["title"]
        channel_data["Subscribers"] = channel["statistics"]["subscriberCount"]
        channel_data["Total Video Count"] = channel["statistics"]["videoCount"]
        channel_data["channel_type"] = channel["snippet"].get("channelType","Unknown")
        channel_data["channel_description"] = channel["snippet"]["description"]
        channel_status = channel.get("status", {}).get("privacyStatus", "Unknown")
        channel_data["channel_status"] = channel_status

        channel_data["Playlist"] = get_playlist_data(channel_id)
    return channel_data

# Get playlist data using Google API
def get_playlist_data(channel_id):
    try:
        playlists = []

        # Retrieve the playlist IDs for the channel
        response = youtube_service.playlists().list(
            part="snippet",
            channelId=channel_id,
            maxResults=10
        ).execute()

        for playlist in response.get("items", []):
            playlist_id = playlist["id"]
            playlist_title = playlist["snippet"]["title"]

            # Retrieve the video details for each playlist
            videos = get_playlist_videos(playlist_id)
            playlist_data = {
                "Playlist ID": playlist_id,
                "Playlist Title": playlist_title,
                "Videos": videos
            }

            playlists.append(playlist_data)

        return playlists

    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return []

# Get playlist video data using Google API
def get_playlist_videos(playlist_id):
    try:
        videos = []

        # Retrieve the video details for the playlist
        response = youtube_service.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=5
        ).execute()

        for video_item in response.get("items", []):
            video_id = video_item["snippet"]["resourceId"]["videoId"]
            video_title = video_item["snippet"]["title"]
            video_description = video_item["snippet"]["description"]

            # Fetch additional video details
            video_details = get_video_details(video_id)
            video_data = {
                "Video ID": video_id,
                "Title": video_title,
                "Description": video_description,
                "Details": video_details
            }

            videos.append(video_data)

        return videos

    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return []

# Get video details using Google API
def get_video_details(video_id):
    try:
        # Retrieve the video details
        response = youtube_service.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        ).execute()

        if response.get("items"):
            video = response["items"][0]
            video_details = {
                "Published Date": video["snippet"]["publishedAt"],
                "View Count": video["statistics"].get("viewCount", 0),
                "Like Count": video["statistics"].get("likeCount", 0),
                "Dislike Count": video["statistics"].get("dislikeCount", 0),
                "Comment Count": video["statistics"].get("commentCount", 0),
                "Duration": video["contentDetails"].get("duration", "Unknown"),
                "thumbnail": video["snippet"]["thumbnails"]["default"]["url"],
                "caption_status": video["snippet"].get("caption", "N/A"),
                "Comments" :get_video_comments(video_id)
            }
            return video_details

    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return {}

# Get video comments using Google API
def get_video_comments(video_id):
    try:
        response = youtube_service.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=5
        ).execute()

        comments = []
        for comment_item in response["items"]:
            comment_snippet = comment_item["snippet"]["topLevelComment"]["snippet"]
            comment_text = comment_snippet["textDisplay"]
            comment_author = comment_snippet["authorDisplayName"]
            comment_published_date = comment_snippet["publishedAt"]

            comment_data = {
                "comment_text": comment_text,
                "comment_author": comment_author,
                "comment_published_date": comment_published_date
            }

            comments.append(comment_data)

    except HttpError as e:
        if e.resp.status == 403 and "commentsDisabled" in str(e):
            # Comments are disabled for the video
            comments = []
        else:
            # Other HTTP error occurred
            raise

    return comments

# Store data in MongoDB
def store_data_in_mongodb():
    st.header("Store Data in MongoDB")
    channel_id = st.text_input("Enter the YouTube channel ID")

    if st.button("Store Data"):
        channel_data = get_channel_data(channel_id)
        mongo_db.channels.insert_one(channel_data)
        st.write("Channel Name :",channel_data["Channel Name"])
        st.write("Subscribers :",channel_data["Subscribers"])
        st.write("Total Video Count :", channel_data["Total Video Count"])

# Migrate data to SQL
def migrate_data_to_sql():
    st.header("Migrate Data to SQL")

    channel_names = [channel["Channel Name"] for channel in mongo_db.channels.find({}, {"Channel Name": 1})]

    # Create a dropdown to select a channel
    selected_channel = st.selectbox("Select a channel", channel_names)

    if st.button("Migrate Data"):
        channel_data = mongo_db.channels.find_one({"Channel Name":selected_channel})

        if channel_data:
            create_sql_tables()
            insert_data_to_sql(channel_data)
            st.write("Data migrated to SQL successfully.")
        else:
            st.write("Channel data not found in MongoDB.")

# Create SQL tables
def create_sql_tables():
    # Create channel table
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            subscribers INT,
            video_count INT
        )
    """)

    # Create playlist table
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS playlist (
            id INT AUTO_INCREMENT PRIMARY KEY,
            channel_id INT,
            playlist_id VARCHAR(255),
            playlist_name VARCHAR(255),
            FOREIGN KEY (channel_id) REFERENCES channel(id)
        )
    """)

    # Create video table
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS video (
            id INT AUTO_INCREMENT PRIMARY KEY,
            playlist_id INT,
            video_id VARCHAR(255),
            title VARCHAR(255),
            description TEXT,
            published_date DATETIME,
            views INT,
            likes INT,
            dislikes INT,
            comment_count INT,
            duration INT,
            thumbnail VARCHAR(255),
            caption_status VARCHAR(255),
            FOREIGN KEY (playlist_id) REFERENCES playlist(id)
        )
    """)

    # Create comment table
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS comment (
            id INT AUTO_INCREMENT PRIMARY KEY,
            video_id INT,
            comment_text TEXT,
            comment_author VARCHAR(255),
            comment_published_date DATETIME,
            FOREIGN KEY (video_id) REFERENCES video(id)
        )
    """)

    mysql_connection.commit()

# Insert data into SQL tables
def insert_data_to_sql(channel_data):
    channel_values = (channel_data["Channel Name"], channel_data["Subscribers"], channel_data["Total Video Count"])
    mysql_cursor.execute("""
        INSERT INTO channel (name, subscribers, video_count)
        VALUES (%s, %s, %s)
    """, channel_values)
    channel_id = mysql_cursor.lastrowid

    for playlist_data in channel_data["Playlist"]:
        playlist_values = (channel_id, playlist_data["Playlist ID"], playlist_data["Playlist Title"])
        mysql_cursor.execute("""
            INSERT INTO playlist (channel_id, playlist_id, playlist_name)
            VALUES (%s, %s, %s)
        """, playlist_values)
        playlist_id = mysql_cursor.lastrowid

    for video_data in playlist_data["Videos"]:

        # Extract the published date from video_data
        published_date_str = video_data["Details"]["Published Date"]
        # Convert the published date string to a datetime object
        published_date = datetime.strptime(published_date_str, '%Y-%m-%dT%H:%M:%SZ')
        # Convert the datetime object to the desired format for MySQL
        formatted_published_date = published_date.strftime('%Y-%m-%d %H:%M:%S')

        duration_str = video_data["Details"]["Duration"]

        # Extract the minutes and seconds from the duration string
        matches = re.search(r'PT((\d+)H)?((\d+)M)?((\d+)S)?', duration_str)
        hours = int(matches.group(2)) if matches.group(2) else 0
        minutes = int(matches.group(4)) if matches.group(4) else 0
        seconds = int(matches.group(6)) if matches.group(6) else 0

        # Calculate the duration in seconds
        duration = hours * 3600 + minutes * 60 + seconds

        video_values = (playlist_id, video_data["Video ID"], video_data["Title"], video_data["Description"],
                        formatted_published_date,  # Use the formatted datetime here
                        video_data["Details"]["View Count"],
                        video_data["Details"]["Like Count"],
                        video_data["Details"]["Dislike Count"],
                        video_data["Details"]["Comment Count"],
                        duration,
                        video_data["Details"]["thumbnail"],
                        video_data["Details"]["caption_status"])

        mysql_cursor.execute("""
            INSERT INTO video (
                playlist_id,
                video_id,
                title,
                description,
                published_date,
                views,
                likes,
                dislikes,
                comment_count,
                duration,
                thumbnail,
                caption_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, video_values)
        video_id = mysql_cursor.lastrowid

        for comment_text in video_data["Details"]["Comments"]:
            # Extract the published date from video_data
            published_date_str = comment_text["comment_published_date"]
            # Convert the published date string to a datetime object
            published_date = datetime.strptime(published_date_str, '%Y-%m-%dT%H:%M:%SZ')
            # Convert the datetime object to the desired format for MySQL
            formatted_published_date = published_date.strftime('%Y-%m-%d %H:%M:%S')

            comment_values = (video_id, comment_text["comment_text"],
                              comment_text["comment_author"],
                              formatted_published_date)
            mysql_cursor.execute("""
                INSERT INTO comment (video_id, comment_text,comment_author,comment_published_date)
                VALUES (%s, %s, %s, %s)
            """, comment_values)

    mysql_connection.commit()

# Search in SQL database
def search_sql_database():
    st.header("Search in SQL Database")
    data = [
        "What are the names of all the videos and their corresponding channels?",
        "Which channels have the most number of videos, and how many videos do they have?",
        "What are the top 10 most viewed videos and their respective channels?",
        "How many comments were made on each video, and what are their corresponding video names?",
        "Which videos have the highest number of likes, and what are their corresponding channel names?",
        "What is the total number of likes and dislikes for each video, and what are their corresponding video names?",
        "What is the total number of views for each channel, and what are their corresponding channel names?",
        "What are the names of all the channels that have published videos in the year 2022?",
        "What is the average duration of all videos in each channel, and what are their corresponding channel names?",
        "Which videos have the highest number of comments, and what are their corresponding channel names?"
    ]

    # Function to execute based on selected option
    def execute_function(option):
        if option == data[0]:
            query ="""
    SELECT v.title, c.name
    FROM video v,channel c,playlist p
    where c.id = p.channel_id and p.id = v.playlist_id
"""
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()
            df = pd.DataFrame(results, columns=['Video Name', 'Channel Name'])

            # Display the results as a table
            st.table(df)
            # Close the database connection
            # conn.close()

        elif option == data[1]:
            query = """
                SELECT name,video_count
                FROM channel
                ORDER BY video_count DESC
                LIMIT 1;
            """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()
            df = pd.DataFrame(results, columns=[ 'Channel Name','Video Count'])

            # Display the results as a table
            st.table(df)
            # Close the database connection
            # conn.close()
        elif option == data[2]:
            query = """SELECT v.title, c.name
            FROM video v
            JOIN playlist p ON v.playlist_id = p.id
            JOIN channel c ON c.id = p.channel_id
            ORDER BY v.duration DESC
            LIMIT 10
            """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()
            df = pd.DataFrame(results, columns=['Video Name', 'Channel name'])
            # Display the results as a table
            st.table(df)

        elif option == data[3]:
            query = """SELECT v.title, v.comment_count
             FROM video v,channel c,playlist p
             where c.id = p.channel_id and p.id = v.playlist_id
             order by  v.comment_count desc
                        """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()
            df = pd.DataFrame(results, columns=['Video Name', 'Comment Count'])
            # Display the results as a table
            st.table(df)

        elif option == data[4]:
            query = """SELECT v.title, v.likes,c.name
            FROM video v,channel c,playlist p
            where c.id = p.channel_id and p.id = v.playlist_id
            order by  v.likes desc
            """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()

            df = pd.DataFrame(results, columns=['Video Name','Video Likes', 'Channel name'])
            # Display the results as a table
            st.table(df)
        elif option == data[5]:
            query = """SELECT v.title, v.likes,v.dislikes
                        FROM video v,channel c,playlist p
                        where c.id = p.channel_id and p.id = v.playlist_id
                        order by  v.likes desc
                        """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()

            df = pd.DataFrame(results, columns=['Video Name', 'Video Likes','Video Dislikes'])
            # Display the results as a table
            st.table(df)
        elif option == data[6]:
            query = """select c.name,sum(v.views) as total_views
            from channel c,video v,playlist p
            where c.id = p.channel_id and p.id = v.playlist_id
            group by c.name
            """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()

            df = pd.DataFrame(results, columns=['Channel Name', 'Total Views'])
            # Display the results as a table
            st.table(df)
        elif option == data[7]:
            query = """SELECT c.name, v.published_date
            FROM channel c
            JOIN playlist p ON c.id = p.channel_id
            JOIN video v ON p.id = v.playlist_id
            WHERE YEAR(v.published_date) = 2022;
            """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()

            df = pd.DataFrame(results, columns=['Channel Name', 'Published Date'])
            # Display the results as a table
            st.table(df)
        elif option == data[8]:
            query = """SELECT c.name, AVG(v.duration) AS avg_duration
            FROM channel c
            JOIN playlist p ON c.id = p.channel_id
            JOIN video v ON p.id = v.playlist_id
            GROUP BY c.name;
            """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()

            df = pd.DataFrame(results, columns=['Channel Name', 'Avg Duration'])
            # Display the results as a table
            st.table(df)
        elif option == data[9]:
            query = """SELECT v.title, v.comment_count, c.name
            FROM channel c
            JOIN playlist p ON c.id = p.channel_id
            JOIN video v ON p.id = v.playlist_id
            WHERE v.comment_count = (SELECT MAX(comment_count)
            FROM video
            WHERE playlist_id = v.playlist_id)
            """
            mysql_cursor.execute(query)
            results = mysql_cursor.fetchall()

            df = pd.DataFrame(results, columns=['Video Name','Video count','Channel Name'])
            # Display the results as a table
            st.table(df)

    selected_option = st.selectbox("Select a search option", data)
    # Execute function based on selected option
    if st.button("Execute"):
        execute_function(selected_option)
# Run the app
if __name__ == "__main__":
    main()
