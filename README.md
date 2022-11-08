# blind-prophet
For the Blind Prophet Discord ~~Gsheet~~ bot.

## Required env variables:
* **BOT_TOKEN**: The token for your bot as found on the Discord Developer portal. See this documentation for more details: https://docs.pycord.dev/en/master/discord.html
* **DATABASE_URL** Postgres database URL
* **GOOGLE_SA_JSON**: Json of your Google service account (used for Google Sheets calls). More information on setting that up can be found here: https://docs.gspread.org/en/latest/oauth2.html
* **COMMAND_PREFIX**: The command prefix used for this bot's commands. For example, '>' would be the command prefix in `>rp @TestUser`
* **SPREADSHEET_ID**: The ID *only* of the BPdia Google Sheets workbook. This can be found in the URL of the workbook when viewed in your browser.
* **SPREADSHEET_ID**: The ID *only* of the Inventory Google Sheets workbook. This can be found in the URL of the workbook when viewed in your browser.
* **DASHBOARD_REFRESH_INTERVAL**: Refresh interval for dashboards. *Recommend 1 min for DEV and 15 for deployed environments*

## Roles:
All assumed roles by the bot.
* **Magewright**: Archivist/Log masters. Wizards of the DB
* **Loremaster**: Adventure/Lore overseer
* **Lead DM**: Helps manage adventures/DM's
* **Quester**: Players eligible for adventures
* **Bots**: Bots....
* **Fledgling**: Members who have yet to create a character

### Faction Roles
Used by the faction commands. Each faction should have a Role with the same name
* **Guild Initiate**: Inital role for starting characters 
* **Guild Member**: Role for characters who have completed initial quests
* **Order of the Copper Dragons**: Nerds
* **Silent Whispers**: Naruto fans
* **Silver Wolves**: #TeamJacob
* **Crimson Blades**: Lookin for a fight
* **Clover Conclave**: Likes trees
* **Sunstone Lotus**: Huff paint
* **Falcon Eyes**: Reads/watches a lot of Sherlock Holmes
* **Azure Guardians**: Thicc blue line