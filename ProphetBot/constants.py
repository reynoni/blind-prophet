from typing import Dict

# Users
ADMIN_USERS = [286360249659817984, 208388527401074688]

# Roles - Maybe these should be in a settings file
TRACKERS_ROLE_BP = 685693338472415309
COUNCIL_ROLE_BP = 679752344157945949
TRACKERS_ROLE = 728637444114874379
COUNCIL_ROLE = 728637447340032062

# Misc
ACTIVITY_TYPES = ["RP", "ARENA", "PIT", "BUY", "SELL", "GLOBAL", "BONUS", "QUEST", "CAMPAIGN", "ADVENTURE",
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
LEVEL_HELP = '@Tracker only\n\nUsage: >level @user'
UPDATE_HELP = '@Tracker only\n\nUsage: >update'
WEEKLY_HELP = '@Council only\n\nUsage: >weekly'
LOG_HELP = '@Trackers only\n\nUsage: >log @player activity [result] [gp] [xp]\n\nAccepted activity types:\n'\
           + str(ACTIVITY_TYPES)
GET_HELP = 'Usage: >get [@user]\n\nIf no @user is specified, it retrieves information for the message author'
CREATE_HELP = '@Council only\n\nUsage: >create @player name faction class starting_GP'
