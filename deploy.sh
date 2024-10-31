cd ~/TelegramBot/
git pull origin master
pip install -r requirements.txt
cd ../../etc/systemd/system/
systemctl stop telemusicbot.service
systemctl start telemusicbot.service
