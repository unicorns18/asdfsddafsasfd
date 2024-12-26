# Discord Bot with Google Drive Integration

A Discord bot application that integrates with Google Drive and provides database functionality.

## Features

- Discord bot functionality using Python
- Google Drive integration for file management
- Database support for persistent storage
- Extension system for modular functionality

## Project Structure

- `app.py` - Main application entry point
- `drive.py` - Google Drive integration functionality
- `database.py` - Database management and operations
- `extensions/` - Directory containing bot extensions
- `utils/` - Utility functions and helper modules
- `credentials/` - Directory for storing authentication credentials
- `guilds.json` - Configuration file for Discord guilds
- `requirements.txt` - Python package dependencies

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your credentials:
   - Place your Discord bot token in the appropriate configuration
   - Set up Google Drive API credentials in the `credentials` directory

3. Start the bot:
```bash
python app.py
```

## Configuration

The bot can be configured through the following files:
- `guilds.json` - Discord guild-specific settings
- Credential files in the `credentials` directory for API authentication

## Dependencies

See [requirements.txt](requirements.txt) for a complete list of Python package dependencies.