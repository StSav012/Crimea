#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import configparser
import os
import os.path
import re

# sending email
import smtplib
import socket
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import numpy as np

from utils import take_webcam_shot


def send_email(config_name: str, body: str):
    if os.path.exists(config_name):
        config = configparser.ConfigParser()
        config.read(config_name)
    else:
        return

    if config is not None:
        server = config.get('email', 'server', fallback='')
        port = config.getint('email', 'port', fallback=0)
        sender = config.get('email', 'login', fallback='')
        password = config.get('email', 'password', fallback='')
        cc = re.findall(r"[\w.@]+", config.get('email', 'recipients', fallback=''))
        if server and port and sender and password and cc:
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = cc[0]
            msg['Cc'] = ','.join(cc[1:])
            msg['Subject'] = 'Qara Dag Notification'
            msg.attach(MIMEText(body, 'plain'))

            photo: bytes = take_webcam_shot()
            if photo:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(photo)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment',
                                filename=f'webcam_photo_{time.strftime("%Y-%m-%d_%H-%M")}.jpg')
                msg.attach(part)

            mail_server_connected: bool = False
            # FIXME: sometimes, it becomes an infinite loop
            while not mail_server_connected:
                try:
                    server = smtplib.SMTP(server, port)
                except OSError:
                    print(socket.gethostbyname(server))
                    time.sleep(60)
                else:
                    mail_server_connected = True
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, cc + [sender], msg.as_string())
            server.quit()


def main():
    ap = argparse.ArgumentParser(description='sends a notification via e-mail')
    ap.add_argument('-c', '--config', help='configuration file', default=os.path.splitext(__file__)[0] + '.ini')
    ap.add_argument('-m', '--message', help='message body', default='')
    args = ap.parse_args()

    send_email(args.config, args.message)


if __name__ == '__main__':
    main()
