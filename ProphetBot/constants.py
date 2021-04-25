from typing import Dict

# Users
ADMIN_USERS = [286360249659817984, 208388527401074688]

# Misc
ACTIVITY_TYPES = ["RP", "ARENA_OLD", "PIT", "BUY", "SELL", "GLOBAL", "BONUS", "QUEST", "CAMPAIGN",
                  "SHOP", "SHOPKEEP", "MOD", "ADMIN"]
SHOP_TYPES = ['BLACKSMITH', 'CONSUMABLE', 'MAGIC', 'WONDROUS', 'POTION', 'POTIONS', 'SCROLL', 'SCROLLS', 'WEAPON',
              'WEAPONS', 'ARMOR', 'ARMORS', 'ARMOUR', 'ARMOURS']
RARITY_MAP: Dict[str, int] = {'COMMON': 1, 'UNCOMMON': 2, 'RARE': 3, 'VERY RARE': 4, 'VERY': 4, 'LEGENDARY': 5,
                              'C': 1, 'U': 2, 'R': 3, 'V': 4, 'VR': 4, 'L': 5}

# Errors
NAME_ERROR = 'Error: The @Name (1) was entered incorrectly. Please try again.'
ACTIVITY_ERROR = 'Error: The activity (2) was entered incorrectly. Please try again.'
RESULT_ERROR = 'Error: The result (3) was entered incorrectly. Please try again.'
NUMBER_ERROR = 'Error: A number was entered incorrectly. Please try again.'
MISSING_FIELD_ERROR = 'Error: One or more fields missing for activity type. Please try again.'
EXTRA_FIELD_ERROR = 'Error: Too many fields for activity type. Please try again.'
INPUT_ERROR = 'Error: There was an incorrect input. Please try again.'
XP_ERROR = 'Error: The targeted player has over 2000 XP. Please enter manually.'
SHOP_TYPE_ERROR = f'Error: The Shop type is unrecognized. Accepted shop types are:\n' \
                  f'{SHOP_TYPES}'

# Help Text
LEVEL_HELP = '**@Magewright/Council only**\n\n' \
             'Usage: `>level @user`'
UPDATE_HELP = '@Tracker only\n\n' \
              'Usage: `>update`'
WEEKLY_HELP = '@Council only\n\n' \
              'Usage: `>weekly`'
LOG_HELP = '**@Magewright/Council only**\n\n' \
           'Logs an activity for a user.\n\n' \
           'General Usage: `>log @player activity [result] [gp] [xp]`\n' \
           'RP: `>log @player rp` - Logs a RP for @player\n' \
           'Arena: `>log @player arena win` - Logs an arena win for @player\n' \
           'Pit: `>log @player pit loss` - Logs a pit loss for @player\n' \
           'Bonus: `>log @player bonus \'because reasons\' 25 25` - Logs a bonus for @player with reason' \
           ' \'because reasons\' and GP/XP values of 25\n\n' \
           'Accepted activity types:\n' + str(ACTIVITY_TYPES)
LOG_ALIAS_HELP = '**@Magewright/Council only**\n\n' \
               'Shorthand for logging a particular activity. For example, `>rp @player` logs a RP for that player,' \
               ' while `>bonus @player \"great job\" 50 50` logs a bonus for that player with a reason of' \
               ' \"good job\" and GP and XP values of 50\n\n' \
               'Usage: `>[activity_type] @player [result] [gp] [xp]`\n\n' \
               'Accepted activity types:\n' \
               + str(ACTIVITY_TYPES)
GET_HELP = 'Usage: `>get [@user]`\n\n' \
           'If no @user is specified, it retrieves information for the message author'
CREATE_HELP = '**@Magewright/Council** only\n\n' \
              'Usage: `>create @player name class starting_GP`'
