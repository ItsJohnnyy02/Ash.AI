import discord
import mariadb
import os
import json
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Discord token and database credentials from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

# Check if all environment variables are loaded
if not all([DISCORD_TOKEN, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
    print("Error: One or more environment variables are missing.")
    exit(1)

# Print the Discord token for debugging
print(f"DISCORD_TOKEN: {DISCORD_TOKEN}")  # Remove in production

# Set up bot with slash commands using app_commands
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to get a database connection
def get_db_connection():
    try:
        port = int(os.getenv("DB_PORT", "3306"))
        conn = mariadb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=port,
            database=DB_NAME
        )
        return conn
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return None

# Function to fetch item data from the database
def get_item_data(item_type, category=None):
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        # Base query to search for items by name (no recipe exclusion)
        query = """
        SELECT guid, section, data 
        FROM codex 
        WHERE LOWER(JSON_UNQUOTE(JSON_EXTRACT(data, '$.itemName'))) LIKE LOWER(%s)
        """
        params = ('%' + item_type + '%',)

        # Add category filter based on gameplayTags
        if category:
            query += " AND JSON_SEARCH(LOWER(data->'$.gameplayTags.gameplayTags[*].tagName'), 'one', LOWER(%s)) IS NOT NULL"
            params = ('%' + item_type + '%', f'Item.Gear.Armor.{category}')

        cursor.execute(query, params)
        items = cursor.fetchall()

        if items:
            print(f"Found {len(items)} items: {[json.loads(item[2]).get('itemName') for item in items]}")
            return items
        else:
            category_text = f" in category '{category}'" if category else ""
            print(f"No items found for item name: {item_type}{category_text}")
            return []

    except mariadb.Error as e:
        print(f"Database error in get_item_data: {e}")
        return []
    finally:
        conn.close()

# Function to fetch hunting creature data from the database
def get_hunt_data(hunt_name: str):
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)  # Return rows as dictionaries
        query = "SELECT guid, data FROM hunting_creature"
        cursor.execute(query)
        results = cursor.fetchall()

        # Filter results based on hunt_name in the JSON data
        matching_hunts = []
        for row in results:
            try:
                data = json.loads(row["data"])
                name = data.get("name", "")
                display_name = data.get("_displayName", "")

                # Check if hunt_name matches name or display_name
                if hunt_name.lower() in name.lower() or hunt_name.lower() in display_name.lower():
                    matching_hunts.append((row["guid"], data))
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON data for row {row['guid']}: {e}")

        return matching_hunts
    except mariadb.Error as e:
        print(f"Database error in get_hunt_data: {e}")
        return []
    finally:
        conn.close()

# Function to fetch mob data from the database
def get_mob_data(mob_name):
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        query = """
        SELECT guid, section, data 
        FROM codex 
        WHERE section = 'mobs' 
        AND (LOWER(JSON_UNQUOTE(JSON_EXTRACT(data, '$.name'))) LIKE LOWER(%s) 
             OR LOWER(JSON_UNQUOTE(JSON_EXTRACT(data, '$._displayName'))) LIKE LOWER(%s))
        """
        cursor.execute(query, ('%' + mob_name + '%', '%' + mob_name + '%'))
        mobs = cursor.fetchall()

        if mobs:
            print(f"Found {len(mobs)} mobs: {mobs}")
            return mobs
        else:
            print(f"No mobs found for name: {mob_name}")
            return []

    except mariadb.Error as e:
        print(f"Database error in get_mob_data: {e}")
        return []
    finally:
        conn.close()

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s) globally: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Slash Command: /item
@bot.tree.command(name="item", description="Fetch items of a certain type, optionally by category (light, medium, heavy)")
async def item(interaction: discord.Interaction, item_type: str, category: str = None):
    print(f"Received /item command with item_type: {item_type}, category: {category}")
    await interaction.response.defer(thinking=True)

    items = get_item_data(item_type, category)

    if not items:
        category_text = f" in category '{category}'" if category else ""
        await interaction.followup.send(f"No {item_type} items found{category_text}.")
        return

    # Check if the user explicitly requested a recipe
    is_recipe_request = item_type.lower().startswith("recipe:")

    if is_recipe_request:
        # Look for an exact recipe match
        recipe_items = [item for item in items if json.loads(item[2]).get("itemName", "").lower() == item_type.lower()]
        if recipe_items:
            items = recipe_items  # Use only the recipe item
        else:
            await interaction.followup.send(f"No recipe found for '{item_type}'.")
            return
    else:
        # Filter out recipes unless explicitly requested
        items = [item for item in items if not json.loads(item[2]).get("itemName", "").lower().startswith("recipe:")]

    if not items:
        category_text = f" in category '{category}'" if category else ""
        await interaction.followup.send(f"No non-recipe {item_type} items found{category_text}.")
        return

    # Handle multiple items (list view)
    if len(items) > 1:
        print(f"Multiple items found: {len(items)}")
        item_names = [json.loads(item[2]).get("itemName", "Unnamed Item") for item in items]
        category_text = f" in category '{category}'" if category else ""
        header = f"Found {len(items)} items matching '{item_type}'{category_text}:\n"
        footer = "\n\nPlease search for any items in this list."
        
        item_list = ""
        max_chars = 2000 - len(header) - len(footer) - 100
        truncated = False
        
        for name in item_names:
            next_line = f"- {name}\n"
            if len(item_list) + len(next_line) <= max_chars:
                item_list += next_line
            else:
                truncated = True
                break
        
        response = header + item_list
        if truncated:
            response += f"(Showing partial results of {len(items)} total. Refine your search for more details.)\n"
        response += footer
        
        if len(response) > 2000:
            response = f"Found {len(items)} items matching '{item_type}'{category_text}. Too many to list (over 2000 characters). Please refine your search."
        
        print(f"Sending list response, length: {len(response)}")
        await interaction.followup.send(response)

    # Handle single item (detailed embed)
    elif len(items) == 1:
        print(f"Single item found: {json.loads(items[0][2]).get('itemName', 'Unnamed Item')}")
        guid, section, data = items[0]
        item_data = json.loads(data)

        item_name = item_data.get("itemName", "Unnamed Item")
        description = item_data.get("description", "No description available.")
        level = item_data.get("level", "N/A")
        rarity_min = item_data.get("rarityMin", "Common")
        rarity_max = item_data.get("rarityMax", "Legendary")
        equip_slots = ", ".join(item_data.get("equipSlots", ["N/A"]))

        embed = discord.Embed(
            title=item_name,
            description=description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Rarity", value=f"{rarity_min} to {rarity_max}", inline=True)
        embed.add_field(name="Equip Slot", value=equip_slots, inline=True)
        embed.add_field(name="Section", value=section or "N/A", inline=True)

        if category:
            embed.add_field(name="Category", value=category.capitalize(), inline=True)

        crafting_recipes = item_data.get("_craftingRecipes", [])
        if crafting_recipes:
            recipe = crafting_recipes[0]
            materials = "\n".join(
                f"{cost['quantity']}x {cost['_item']['itemName']}"
                for cost in recipe.get("generalResourceCost", [])
            )
            embed.add_field(
                name="Crafting Recipe",
                value=materials or "No materials specified.",
                inline=False
            )

        sold_by = item_data.get("_soldBy", [])
        sold_by_text = "\n".join(
            f"{vendor['_characterName']} ({vendor['name']})" for vendor in sold_by
        ) if sold_by else "Not sold by any vendors."
        embed.add_field(name="Sold By", value=sold_by_text, inline=False)

        reward_from = item_data.get("_rewardFrom", [])
        reward_from_text = "\n".join(
            str(reward) for reward in reward_from[:5]
        ) + ("..." if len(reward_from) > 5 else "") if reward_from else "No rewards specified."
        embed.add_field(name="Reward From", value=reward_from_text, inline=False)

        # Dropped By (Updated Logic)
        dropped_by = item_data.get("_droppedBy", [])
        if dropped_by:
            dropped_by_text = "\n".join(
                f"{enemy['_displayName']} (Level {enemy['_levelRange']})"
                for enemy in dropped_by[:5]
            ) + ("..." if len(dropped_by) > 5 else "")
        else:
            # Check _droppedIn for location-based drops
            dropped_in = item_data.get("_droppedIn", [])
            if dropped_in:
                dropped_by_text = ""
                for poi in dropped_in:
                    poi_name = poi.get("playerFacingName", "Unknown Location")
                    poi_id = poi.get("guid", "N/A")
                    # Fetch mobs from this POI that match the reward table
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            query = """
                            SELECT data 
                            FROM codex 
                            WHERE section = 'pois' AND guid = %s
                            """
                            cursor.execute(query, (poi_id,))
                            poi_data = cursor.fetchone()
                            if poi_data:
                                poi_json = json.loads(poi_data[0])
                                reward_tables = poi_json.get("pOIRewardTables", [])
                                mobs = []
                                for table in reward_tables:
                                    table_id = table.get("rewardTableId", {}).get("guid", "")
                                    # Check if this matches the emblem's reward table
                                    if table_id in [rt for rt in item_data.get("_rewardFrom", [])] or table_id == "6064632349999038476":  # Adjust based on your data
                                        inclusion_expr = table.get("inclusionExpression", {}).get("expression", "")
                                        if "character.humanoid" in inclusion_expr:
                                            matching_mobs = poi_json.get("matchingRewardTables", [{}])[0].get("matchingMobs", [])
                                            mobs.extend([
                                                f"{mob['_displayName']} (Level {mob['_levelRange']})"
                                                for mob in matching_mobs[:5]
                                            ])
                                if mobs:
                                    dropped_by_text += f"Dropped in {poi_name}:\n" + "\n".join(mobs) + ("..." if len(matching_mobs) > 5 else "")
                                else:
                                    dropped_by_text += f"Dropped in {poi_name} by humanoid enemies."
                            else:
                                dropped_by_text = "Not dropped by any enemies (location data not found)."
                            conn.close()
                        except mariadb.Error as e:
                            print(f"Database error fetching POI data: {e}")
                            dropped_by_text = "Error fetching drop location data."
                    else:
                        dropped_by_text = "Not dropped by any enemies (database connection failed)."
            else:
                dropped_by_text = "Not dropped by any enemies."
        embed.add_field(name="Dropped By", value=dropped_by_text or "Not dropped by any enemies.", inline=False)

        print("Sending detailed embed")
        await interaction.followup.send(embed=embed)

# Slash Command: /hunt
@bot.tree.command(name="hunt", description="Fetch hunting creatures by name")
async def hunt(interaction: discord.Interaction, hunt_name: str):
    print(f"Received /hunt command with hunt_name: {hunt_name}")
    await interaction.response.defer(thinking=True)

    # Query hunt data from the database
    hunts = get_hunt_data(hunt_name)

    if hunts:
        for guid, data in hunts:
            # Debug: Log the JSON data for this creature
            print(f"JSON Data for {hunt_name}:")
            print(json.dumps(data, indent=2))  # Pretty-print the JSON data

            # Extract data from the JSON
            name = data.get("_displayName", data.get("name", "Unknown Creature"))
            description = data.get("description", "No description available.")
            level_range = data.get("_levelRange", "N/A")

            # Extract respawnTime from populationInstances
            respawn_time = "N/A"
            population_instances = data.get("populationInstances", [])
            if population_instances:
                first_instance = population_instances[0]
                respawn_time = first_instance.get("respawnTime", "N/A")  # Extract respawnTime from the first instance

            # Extract location (first instance if available)
            location = "N/A"
            if population_instances:
                first_instance = population_instances[0]
                loc = first_instance.get("location", {})
                location = f"**X:** {loc.get('x', 'N/A')}\n**Y:** {loc.get('y', 'N/A')}\n**Z:** {loc.get('z', 'N/A')}"

            # Extract drops (from _loot array)
            drops = []
            loot_tables = data.get("_loot", [])
            for loot in loot_tables:
                reward_containers = loot.get("rewardDefContainers", [])
                for container in reward_containers:
                    rewards = container.get("rewards", [])
                    for reward in rewards:
                        item_rewards = reward.get("itemRewards", [])
                        for item in item_rewards:
                            item_name = item.get("_item", {}).get("itemName", "Unknown Item")
                            if item_name not in drops:  # Avoid duplicates
                                drops.append(item_name)

            # Format drops text
            drops_text = "\n".join(f"• {drop}" for drop in drops[:5]) + ("\n• ..." if len(drops) > 5 else "") if drops else "No drops specified."

            # Create and send an embed
            embed = discord.Embed(
                title=f"🦌 {name}",
                description=f"*{description}*",
                color=discord.Color.green()
            )
            embed.add_field(name="📊 **Level Range**", value=f"`{level_range}`", inline=True)
            embed.add_field(name="⏳ **Respawn Time**", value=f"`{respawn_time}`", inline=True)  # Add respawnTime
            embed.add_field(name="📍 **Location**", value=f"```{location}```", inline=False)
            embed.add_field(name="🎁 **Drops**", value=f"{drops_text}", inline=False)
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

            print(f"Sending embed for hunt: {name}")
            await interaction.followup.send(embed=embed)
    else:
        print(f"No hunting creatures found, sending fallback message")
        await interaction.followup.send(f"No hunting creatures found matching '{hunt_name}'.")

# Slash Command: /mob
@bot.tree.command(name="mob", description="Fetch mobs by name")
async def mob(interaction: discord.Interaction, mob_name: str):
    print(f"Received /mob command with mob_name: {mob_name}")
    await interaction.response.defer(thinking=True)

    mobs = get_mob_data(mob_name)

    if mobs:
        for mob in mobs:
            guid, section, data = mob
            mob_data = json.loads(data)

            # Debug: Log the JSON data for this mob
            print(f"JSON Data for {mob_name}:")
            print(json.dumps(mob_data, indent=2))  # Pretty-print the JSON data

            # Extract basic mob info
            name = mob_data.get("_displayName", mob_data.get("name", "Unknown Mob"))
            description = mob_data.get("description", "No description available.")
            level_range = mob_data.get("_levelRange", "N/A")

            # Extract respawnTime from populationInstances
            respawn_time = "N/A"
            population_instances = mob_data.get("populationInstances", [])
            if population_instances:
                first_instance = population_instances[0]
                respawn_time = first_instance.get("respawnTime", "N/A")  # Extract respawnTime from the first instance

            # Extract location (first instance if available)
            location = "N/A"
            if population_instances:
                first_instance = population_instances[0]
                loc = first_instance.get("location", {})
                location = f"**X:** {loc.get('x', 'N/A')}\n**Y:** {loc.get('y', 'N/A')}\n**Z:** {loc.get('z', 'N/A')}"

            # Extract drops (from _loot array)
            drops = []
            loot_tables = mob_data.get("_loot", [])
            for loot in loot_tables:
                reward_containers = loot.get("rewardDefContainers", [])
                for container in reward_containers:
                    rewards = container.get("rewards", [])
                    for reward in rewards:
                        item_rewards = reward.get("itemRewards", [])
                        for item in item_rewards:
                            item_name = item.get("_item", {}).get("itemName", "Unknown Item")
                            if item_name not in drops:  # Avoid duplicates
                                drops.append(item_name)

            # Format drops text
            drops_text = "\n".join(f"• {drop}" for drop in drops[:5]) + ("\n• ..." if len(drops) > 5 else "") if drops else "No drops specified."

            # Create embed (same as /hunt but with red color)
            embed = discord.Embed(
                title=f"🧿 {name}",  # Add an emoji for flair
                description=f"*{description}*",  # Italicize the description
                color=discord.Color.red()  # Red color for mobs
            )

            # Add fields with better formatting
            embed.add_field(name="📊 **Level Range**", value=f"`{level_range}`", inline=True)
            embed.add_field(name="⏳ **Respawn Time**", value=f"`{respawn_time}`", inline=True)  # Add respawnTime
            embed.add_field(name="📍 **Location**", value=f"```{location}```", inline=False)
            embed.add_field(name="🎁 **Drops**", value=f"{drops_text}", inline=False)

            # Add a thumbnail (optional, replace with a relevant image URL)
            embed.set_thumbnail(url="https://i.imgur.com/xyz1234.png")  # Replace with your image URL

            # Add a footer with additional info
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

            print(f"Sending embed for mob: {name}")
            await interaction.followup.send(embed=embed)
    else:
        print(f"No mobs found, sending fallback message")
        await interaction.followup.send(f"No mobs found matching '{mob_name}'.")

# Run the bot
bot.run(DISCORD_TOKEN)
