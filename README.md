# wu-blackhole
A [Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot) than upload file/folders to a [Telegram](https://telegram.org/) Channel. No matter the file/folder size, it will be fragmented and mapped into a [SQLite](https://www.sqlite.org) Database for retrieval via [Flask](https://palletsprojects.com/p/flask/)\/[Vue.js](https://vuejs.org/)




#### Log Level
|Level   |Value |
|--------|:----:|
|Debug   |  10  |
|Info    |  20  |
|Warning |  30  |
|Error   |  40  |



#### Temporary Notes:
* Max block size is 50M. Some encryption methods may increase the final file size. be careful about that and do not use max limit.
* Do not change block size while there is items in queue.