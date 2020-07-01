import discord
import logging
import re
from ProphetBot.cogs.constants import *
from discord.ext import commands
import importlib.util
from texttable import Texttable

# NEVER COPY OVER THIS
gloc = 'C:\\Users\\Nick\\ProphetBot\\cogs\\mod\\gsheet.py'
# gloc = 'D:\\OneDrive\\Scripts\\Public\\ProphetBot\\cogs\\mod\\gsheet.py'


spec = importlib.util.spec_from_file_location("gsheet", gloc)
foo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(foo)
sheet = foo.gsheet()
SPREADSHEET_ID = '156aVcYNPLE2OAO8Ga78zmxciCrKIzCzXSn7-cQFbSMY'
BOT_SPREADSHEET_ID = '1Hm-WthWv_kwBeUlB_ECzcltveasT7QwuWudk76v1uoQ'
global USERLIST
global ASL
global XPLIST


def merge(list1, list2):
    logging.info(f'{list1}')
    logging.info(f'{list2}')
    merged_list = [(list1[i], list2[i]) for i in range(0, len(list1))]
    return merged_list


def updateUserlist():
    RENDER_OPTION = "UNFORMATTED_VALUE"
    LIST_RANGE = 'Characters!A3:A'
    USERLIST = sheet.get(SPREADSHEET_ID, LIST_RANGE, RENDER_OPTION)
    USERLIST = USERLIST['values']
    return USERLIST


def updateASL():
    RENDER_OPTION = "UNFORMATTED_VALUE"
    ASL_RANGE = 'Characters!B1'
    ASL = sheet.get(SPREADSHEET_ID, ASL_RANGE, RENDER_OPTION)
    ASL = int(ASL['values'][0][0])
    return ASL


def updateXPlist():
    RENDER_OPTION = "FORMATTED_VALUE"
    XPLIST_RANGE = 'Characters!H3:H'
    XPLIST = sheet.get(SPREADSHEET_ID, XPLIST_RANGE, RENDER_OPTION)
    XPLIST = XPLIST['values']
    USERLIST = updateUserlist()
    XPLIST = merge(USERLIST, XPLIST)
    return XPLIST


def getCL(id):
    IDINDEX = USERLIST.index(id)
    CL = XPLIST[IDINDEX][1][0]
    CL = 1 + round(int(CL) / 1000)
    return CL


USERLIST = updateUserlist()
XPLIST = updateXPlist()
ASL = updateASL()
CL = getCL(['286360249659817984'])

print("XPLIST:" + f'{XPLIST}')
print("USERLIST:" + f'{USERLIST}')
print("ASL:" + f'{ASL}')
print("CL:" + f'{CL}')


class mgmt(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def level(self, ctx):
        XPLIST_RANGE = 'Characters!H3:H'
        USERLIST = updateUserlist()
        XPLIST = sheet.get(SPREADSHEET_ID, XPLIST_RANGE, RENDER_OPTION)
        XPLIST = XPLIST['values']
        XPLIST = merge(USERLIST, XPLIST)
        con = True
        xpcheck = True
        num = 0
        global nameCheck
        nameCheck = True
        if user_has_role(TRACKERS_ROLE, ctx):
            RANGE_NAME = ''
            msg = ctx.message.content[7:]
            result = [x.strip() for x in msg.split('.')]
            for i in result:
                if num == 0:
                    i = re.sub(r'\D+', '', i)
                    logging.info(f'{i}')
                    if [i] not in USERLIST:
                        logging.info(f'{nameCheck}')
                        nameCheck = False
                        break
                    else:
                        INDEX = USERLIST.index([i])
                        logging.info(f'{INDEX}')
                        CURRENTXPLIST = [x[1] for x in XPLIST]
                        logging.info(f'{CURRENTXPLIST}')
                        CURRENTXP = CURRENTXPLIST[INDEX]
                        logging.info(f'{CURRENTXP}')
                        if int(CURRENTXP[0]) > 2000:
                            xpcheck = False
                            break
                        elif int(CURRENTXP[0]) < 2000:
                            NEWXP = int(CURRENTXP[0]) + 1000
                        else:
                            NEWXP = 1000
                        DATA = []
                        DATA.append([NEWXP])
                        logging.info(f'{NEWXP}')
                        INSERT_RANGE = 'Characters!H' + str(INDEX + 3)
                        logging.info(f'{INSERT_RANGE}')
                        sheet.set(SPREADSHEET_ID, INSERT_RANGE, DATA, "COLUMNS")
                        await ctx.message.channel.send(msg + ' - level up submitted!')
            if nameCheck == False:
                await ctx.message.channel.send('Error: The @Name (1) was entered incorrectly. Please try again.')
            elif xpcheck == False:
                await ctx.message.channel.send('Error: The targeted player has over 2000 XP. Please enter manually.')
        else:
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)

    @commands.command()
    async def get(self, ctx):
        con = True
        msg = ctx.message.content[5:]
        if len(msg) == 0:
            DATA = [str(ctx.author.id)]
        elif len(msg.split()) == 1:
            DATA = msg
            DATA = [re.sub(r'\D+', '', DATA)]
            if DATA in USERLIST:
                con = True
            else:
                con = False
        else:
            con = False

        if con != False:
            IN_RANGE_NAME = 'Bot Staging!A4'
            OUT_RANGE_NAME = 'Bot Staging!A9:B17'
            DATA_IN = str(DATA)
            values = []
            values.append(DATA)
            RENDER_OPTION = "UNFORMATTED_VALUE"
            sheet.set(BOT_SPREADSHEET_ID, IN_RANGE_NAME, values, "COLUMNS")
            DATA_OUT = sheet.get(BOT_SPREADSHEET_ID, OUT_RANGE_NAME, RENDER_OPTION)
            Send_Data = DATA_OUT['values']
            logging.info(f'{Send_Data}')
            t = Texttable()
            t.set_cols_align(["l", "r"])
            t.set_cols_valign(["m", "m"])
            t.add_rows(Send_Data)
            DATA_SEND = t.draw()

            await ctx.send("`" + DATA_SEND + "`")
        else:
            await ctx.send(
                "'" + msg + "' is not a valid input... >get for your own stats, >get @name for someone else.")
        await ctx.message.delete()
        print("success")

    @commands.command()
    async def weekly(self, ctx):
        # Command to process the weekly reset
        if user_has_role(COUNCIL_ROLE, ctx):
            await ctx.channel.send("`PROCESSING WEEKLY RESET`")
            RENDER_OPTION = "UNFORMATTED_VALUE"
            RANGE_NAME_XP_PEND = 'Characters!I3:I'
            RANGE_NAME_XP_TOTAL = 'Characters!H3:H'
            RANGE_NAME_GP_PEND = 'Characters!F3:F'
            RANGE_NAME_GP_TOTAL = 'Characters!E3:E'
            GP_PEND = sheet.get(SPREADSHEET_ID, RANGE_NAME_GP_PEND, RENDER_OPTION)
            XP_PEND = sheet.get(SPREADSHEET_ID, RANGE_NAME_XP_PEND, RENDER_OPTION)
            GP_TOTAL = GP_PEND.get('values', {})
            XP_TOTAL = XP_PEND.get('values', {})
            # print("GP PEND:" + f'{GP_PEND}')
            # print("XP PEND:" + f'{XP_PEND}')
            # print("GP TOTAL:" + f'{GP_TOTAL}')
            # print("XP TOTAL:" + f'{XP_TOTAL}')
            sheet.set(SPREADSHEET_ID, RANGE_NAME_GP_TOTAL, GP_TOTAL, "ROWS")
            sheet.set(SPREADSHEET_ID, RANGE_NAME_XP_TOTAL, XP_TOTAL, "ROWS")
            LOG_RANGE_IN = 'Log!A2:G500'
            LOG_RANGE_OUT = 'Archive Log!A2:G500'
            LOG_IN = sheet.get(SPREADSHEET_ID, LOG_RANGE_IN, RENDER_OPTION)
            LOG_OUT = LOG_IN.get('values', {})
            sheet.add(SPREADSHEET_ID, LOG_RANGE_OUT, LOG_OUT, "ROWS")
            sheet.clear(SPREADSHEET_ID, LOG_RANGE_IN)
            await ctx.message.delete()
            await ctx.channel.send("`WEEKLY RESET HAS OCCURRED.`")
        else:
            await ctx.message.delete()
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return

    @commands.command()
    async def log(self, ctx):
        con = True
        global nameCheck
        global resCheck
        global actCheck
        global numCheck
        global inputCheck
        global DATA
        display_errors = []
        inputCheck = True
        numCheck = True
        resCheck = True
        nameCheck = True
        actCheck = True
        global act
        global USERLIST
        if user_has_role(TRACKERS_ROLE, ctx):  # >log command requires Tracker role
            actCheck = True
            RANGE_NAME = 'Log!A2'
            FIELDS = 6  # Amount of fields/cells
            msg = ctx.message.content[5:]
            log_args = [x.strip() for x in msg.split('.')]
            if 2 < len(log_args) <= FIELDS:
                activity_types = ["RP", "ARENA", "PIT", "BUY", "SELL", "GLOBAL", "BONUS", "QUEST",
                                  "CAMPAIGN", "ADVENTURE", "SHOP", "SHOPKEEP"]
                num = 0
                DATA = []
                DATA.append([ctx.message.author.name])
                DATA.append([str(ctx.message.created_at)])
                # while con == True:
                for arg in log_args:
                    logging.info("num" + f'{num}')
                    logging.info(f'{DATA}')
                    if num == 0:
                        arg = re.sub(r'\D+', '', arg)
                        logging.info(f'{arg}')
                        if [arg] not in USERLIST:
                            logging.info(f'{nameCheck}')
                            display_errors.append(NAME_ERROR)
                            nameCheck = False
                            break
                        else:
                            DATA.append([arg])
                    elif num == 1:
                        logging.info(f'{arg}')
                        if arg.upper() in (act.upper() for act in activity_types):
                            act = arg.upper()
                            logging.info(f'{act}')
                            DATA.append([act])
                            # num = num+1
                            # continue
                        else:
                            logging.info(f'{actCheck}')
                            display_errors.append(ACTIVITY_ERROR)
                            actCheck = False
                            logging.info(f'{actCheck}')
                            break
                    elif num == 2:
                        logging.info(f'{arg}')
                        if act == "RP":
                            if arg not in ["1", "2", "3"]:
                                display_errors.append(RESULT_ERROR)
                                resCheck = False
                                num = num + 1
                                break
                            else:
                                DATA.append([arg])
                                num = num + 1
                                continue
                        elif act == "ARENA" or act == "PIT":
                            if arg.upper() not in ["WIN", "LOSS", "HOST"]:
                                display_errors.append(RESULT_ERROR)
                                resCheck = False
                                num = num + 1
                                break
                            else:
                                DATA.append([arg.upper()])
                                num = num + 1
                                continue
                        elif act == "SHOP" or act == "SHOPKEEP":
                            intcheck = re.sub(r'\D+', '', arg)
                            if intcheck == '':
                                display_errors.append(INPUT_ERROR)
                                inputCheck = False
                                break
                            else:
                                DATA.append([intcheck])
                        else:
                            DATA.append([arg])
                            # num = num+1
                            continue
                    elif num == 3:
                        if arg.isnumeric():
                            DATA.append([int(arg)])
                            num = num + 1
                            continue
                        elif act == "SHOP" or act == "SHOPKEEP":
                            display_errors.append(INPUT_ERROR)
                            inputCheck = False;
                            break
                        else:
                            DATA.append([arg])
                            num = num + 1
                        continue
                    elif num == 4 or num == 5:
                        DATA.append([arg])
                        # num = num+1
                        logging.info(f'{num}')
                    else:
                        DATA.append("Nope")
                    logging.info(f'{num}')
                    num = num + 1
                # logging.info("name check" +f'{nameCheck}')
                # logging.info("act check " +f'{actCheck}')
                # logging.info("con check" +f'{con}')
                if len(display_errors) > 0:
                    for error in display_errors:
                        await ctx.message.channel.send(error)
                else:
                    sheet.add(SPREADSHEET_ID, RANGE_NAME, DATA, "COLUMNS")
                    await ctx.message.channel.send(msg + ' - submitted by ' + ctx.author.nick)
                '''    
                if nameCheck == False:
                    await ctx.message.channel.send('Error: The @Name (1) was entered incorrectly. Please try again.')
                elif actCheck == False:
                    await ctx.message.channel.send('Error: The activity (2) was entered incorrectly. Please try again.')
                elif resCheck == False:
                    await ctx.message.channel.send('Error: The result (3) was entered incorrectly. Please try again.')
                elif numCheck == False:
                    await ctx.message.channel.send('Error: A nunber was entered incorrectly. Please try again.')
                elif inputCheck == False:
                    await ctx.message.channel.send('Error: There was an incorrect input. Please try again.')
                else:
                    sheet.add(SPREADSHEET_ID, RANGE_NAME, DATA, "COLUMNS")
                    await ctx.message.channel.send(msg + ' - submitted by ' + ctx.author.nick)
                '''

            else:
                await ctx.message.channel.send('Error: There must be 3-6 fields entered.'.format(FIELDS, FIELDS - 1))

        else:
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
        await ctx.message.delete()

    @commands.command()
    async def create(self, ctx):
        global USERLIST
        if user_has_role(COUNCIL_ROLE, ctx):
            USERLIST = updateUserlist()
            RANGE_NAME = 'Characters!A' + str(len(USERLIST) + 3)
            XP_RANGE = 'Characters!H' + str(len(USERLIST) + 3)
            msg = ctx.message.content[8:]
            result = [x.strip() for x in msg.split('.')]
            print(f'{result}')
            print(f'{RANGE_NAME}')

            DATA = []
            for i in result:
                if i.startswith("<"):
                    i = re.sub(r'\D+', '', i)
                DATA.append([i])

            DATA2 = []
            DATA2.append(['0'])
            sheet.set(SPREADSHEET_ID, RANGE_NAME, DATA, "COLUMNS")
            sheet.set(SPREADSHEET_ID, XP_RANGE, DATA2, "COLUMNS")
            print(f'{DATA}')
            await ctx.message.delete()
            await ctx.message.channel.send(ctx.message.content[8:] + ' - submitted!')
            USERLIST = updateUserlist()

        else:
            await ctx.message.delete()
            await ctx.message.channel.send('Naughty Naughty ' + ctx.message.author.name)
            return


def setup(bot):
    bot.add_cog(mgmt(bot))


def user_has_role(roleid, ctx):
    roles = ctx.message.author.roles
    for x in roles:
        if roleid == x.id:
            return True
    return False
