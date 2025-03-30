### CodexBot - A Discord Bot for Game Data Lookup

**CodexBot** is a Discord bot designed to provide detailed in-game information by querying a MariaDB database. Built with Python and the `discord.py` library, it offers slash commands to fetch data on items, hunting creatures, and mobs from a game codex. The bot integrates with a database to retrieve and display rich details such as item stats, crafting recipes, mob drops, locations, and more, all presented in user-friendly Discord embeds.

#### Features
- **/item**: Search for items by name, with optional category filtering (e.g., light, medium, heavy armor). Displays detailed stats, crafting recipes, vendors, and drop sources.
- **/hunt**: Retrieve data on hunting creatures, including level ranges, respawn times, locations, and drops.
- **/mob**: Look up mob details, such as level ranges, locations, respawn times, and loot tables.
- **Rich Embeds**: Information is formatted in visually appealing Discord embeds with fields for easy reading.
- **Database Integration**: Connects to a MariaDB database to fetch real-time game data stored in JSON format.
- **Environment Configuration**: Uses a `.env` file for secure management of Discord tokens and database credentials.

#### Prerequisites
- Python 3.8+
- MariaDB database with pre-populated `codex` and `hunting_creature` tables
- Discord bot token (obtained from the Discord Developer Portal)

#### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/ItsJohnnyy02/Ash.AI
   cd codexbot
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your `.env` file with the following variables:
   ```plaintext
   DISCORD_TOKEN=your_discord_bot_token
   DB_USER=your_db_username
   DB_PASSWORD=your_db_password
   DB_HOST=your_db_host
   DB_PORT=3306
   DB_NAME=your_db_name
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

#### Dependencies
- `discord.py`: For Discord bot functionality
- `mariadb`: Python connector for MariaDB
- `python-dotenv`: To load environment variables
- `json`: For parsing JSON data from the database

#### Usage
Invite the bot to your Discord server and use the following slash commands:
- `/item <item_type> [category]`: Fetch item details (e.g., `/item sword heavy`).
- `/hunt <hunt_name>`: Look up hunting creature info (e.g., `/hunt bear`).
- `/mob <mob_name>`: Retrieve mob data (e.g., `/mob goblin`).

#### Database Schema
The bot expects a MariaDB database with at least two tables:
- `codex`: Stores item and mob data with columns `guid`, `section`, and `data` (JSON).
- `hunting_creature`: Stores hunting creature data with columns `guid` and `data` (JSON).

#### Contributing
Feel free to fork this repository, submit issues, or create pull requests to enhance functionality or fix bugs!

#### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

![#codex-chat _ Ashes Codex - MMO Wiki - Discord 3_14_2025 11_22_29 PM](https://github.com/user-attachments/assets/4ef3991b-f683-44ac-990a-6e8692d67f0e)
![#codex-chat _ Ashes Codex - MMO Wiki - Discord 3_14_2025 11_22_14 PM](https://github.com/user-attachments/assets/2068853c-7427-4bc2-9472-d0e3f1616e3b)
![#itemshuntmob _ test - Discord 3_30_2025 9_39_05 AM](https://github.com/user-attachments/assets/5b59fc88-ea3e-453e-958f-1219f2bf549c)


