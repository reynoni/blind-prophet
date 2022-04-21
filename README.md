# blind-prophet
For the Blind Prophet Discord Gsheet bot.

## Required env variables:
* **BOT_TOKEN**: The token for your bot as found on the Discord Developer portal. See this documentation for more details: https://docs.pycord.dev/en/master/discord.html
* **GOOGLE_SA_JSON**: Json of your Google service account (used for Google Sheets calls). More information on setting that up can be found here: https://docs.gspread.org/en/latest/oauth2.html
* **COMMAND_PREFIX**: The command prefix used for this bot's commands. For example, '>' would be the command prefix in `>rp @TestUser`
* **SPREADSHEET_ID**: The ID *only* of the BPdia Google Sheets workbook. This can be found in the URL of the workbook when viewed in your browser.
* **SPREADSHEET_ID**: The ID *only* of the Inventory Google Sheets workbook. This can be found in the URL of the workbook when viewed in your browser.