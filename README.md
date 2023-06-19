# YouTube Data Harvesting

This project is designed to retrieve data from YouTube channels using the YouTube Data API and store it in MongoDB. It also provides functionality to migrate the data to a SQL database and perform various queries on the stored data.

## Prerequisites

Before running this code, make sure you have the following dependencies installed:

- Streamlit
- pymongo
- mysql-connector-python
- pandas
- google-api-python-client

You will also need to obtain a Google API key to access the YouTube Data API.

## Installation

1. Clone this repository:

```bash
git clone https://github.com/your-username/your-repo.git
```

2. Change to the project directory:

```bash
cd your-repo
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Set up your API key:

Replace `"your API key"` with your actual Google API key in the `api_key` variable in the code.

5. Set up your MySQL database:

- Create a MySQL database called "youtube_db".
- Update the MySQL connection details in the code (host, user, password) if necessary.

6. Set up your MongoDB:

- Install MongoDB on your local machine.
- Start the MongoDB service.
- Update the MongoDB connection details in the code (host, port) if necessary.

## Usage

To run the application, execute the following command:

```bash
streamlit run main.py
```

This will start the Streamlit app and open it in your default web browser.

## Functionality

The application provides the following options:

- **Retrieve YouTube Channel Data**: Enter a YouTube channel ID to retrieve the channel's data, including playlists, videos, and comments. The data will be stored in MongoDB.
- **Migrate Data to SQL**: Migrate the data stored in MongoDB to a MySQL database. This includes creating the necessary tables and inserting the data.
- **Search in SQL Database**: Perform various queries on the data stored in the SQL database. Choose from predefined queries to get information such as video and channel names, video counts, views, likes, comments, and more.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
