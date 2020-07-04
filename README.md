# wu-blackhole

## Combining server and client in one GUI app:
* Using [fman build system](https://github.com/mherrmann/fbs) for packaging and deployment.





<br><br><br><br>

## Old server / client
A [Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot) 
than upload file/folders to a [Telegram](https://telegram.org/) User/Channel/Group. 
No matter the file/folder size, it will be fragmented and mapped into a 
[SQLite](https://www.sqlite.org) Database for retrieval via 
~~[PyQt5](https://pypi.org/project/PyQt5/)/~~ [PySide2](https://pypi.org/project/PySide2/) Client (~~[Flask](https://palletsprojects.com/p/flask/)\/[Vue.js](https://vuejs.org/)~~)

After emptying queue, a encrypted backup of database will be uploaded to the blackhole. 
to update client's database, you can copy/past code in the last message with tag of #WBHBackup. 
Client with ask for `backup_pass` and download, decrypt and update your database. 




## Temp for final doc

#### Log Level
|Level   |Value |
|--------|:----:|
|Debug   |  10  |
|Info    |  20  |
|Warning |  30  |
|Error   |  40  |



#### Temporary Notes:
* Max block size is 20M (50MB to send, 20MB to download using bot). Some encryption methods may increase the final file size. be careful about that and do not use max limit.
* Do not change block size while there is items in queue.



### GUI Client



#### Screenshots
|   | |
|--------|:----:|
|![explorer tab](https://raw.githubusercontent.com/WUAmin/wu-blackhole/master/Docs/explorer-tab.png)  | ![settings tab](https://raw.githubusercontent.com/WUAmin/wu-blackhole/master/Docs/settings-tab.png)|
|![restore database](https://raw.githubusercontent.com/WUAmin/wu-blackhole/master/Docs/restore-database.png)    |  ![input password](https://raw.githubusercontent.com/WUAmin/wu-blackhole/master/Docs/input-password.png)|



#### Linux
~~Builing AppImage using Ubuntu 16.04 on docker. ([for more information](https://docs.beeware.org/en/latest/tutorial/tutorial-3.html#creating-your-application-scaffold))
This `_linux-build.sh` remove old builds.~~
```bash
cd docker
docker image build -t blackholeguiclient .
docker run -it -v /path/to/root/of/project:/project --privileged blackholeguiclient
```
* ~~you have to pass your project forlder to docker ( _/path/to/root/of/project_ )~~
* `--privileged` ~~is necessary or you will get error on docker:~~
  ```
  fusermount: mount failed: Operation not permitted
  ```
  

