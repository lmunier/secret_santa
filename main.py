#!/bin/usr/python3
# -*-coding:Utf-8 -*

"""
main.py

Author: Munier Louis
Version: 1.2
Date: 2024-11-06

Script to shuffle and send e-mail in the case of a friendly secret santa.
It gets the list of people from a file, shuffles it, saves it to a file, and
sends mail to each person. It also keeps information from previous years to
avoid sending mail to the same person each time.
"""

from io import StringIO
from ruamel.yaml import YAML
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import os
import re
import getpass
import random
import smtplib
import ssl

yaml = YAML()
yaml.preserve_quotes = True


def main():
    """Main function of the script."""
    list_people = []

    global_config = get_global_config()
    private_config = get_config(global_config["private_folder"])

    # Recover peoples from file
    config_sublist = input("[Question] - Which yaml sublist to take ? [test_config] ")
    if config_sublist == "":
        config_sublist = "test_config"
    elif config_sublist not in private_config:
        print("[ERROR] - This sublist does not exist.")
        return

    list_people = recover_people(global_config["private_folder"], config_sublist)

    # Shuffle list if
    answer = input("[Question] - Would you like to shuffle list ? [y/N] ")
    if answer.lower() == "y":
        random.shuffle(list_people)

    # Save people order
    output_file = os.path.join(
        global_config["private_folder"], config_sublist, "output_mail_list.yaml"
    )
    save_people(list_people, output_file)

    # Send mail
    answer = input("[Question] - Would you like to send mail ? [y/N] ")
    if answer.lower() == "y":
        password = prompt_for_password()

        for idx, people in enumerate(list_people):
            next_people = list_people[(idx + 1) % len(list_people)][0]
            mail_body = create_body(
                people[0], next_people, private_config[config_sublist]["mail_body"]
            )

            send_email(
                mail_body,
                password,
                private_config["smtp_server"],
                private_config["port"],
                sender=private_config["mail_sender"],
                recipient=people[1],
                subject=private_config[config_sublist]["mail_subject"],
            )


def get_global_config() -> dict:
    """
    Reads the global configuration from a YAML file and returns it as a dictionary.

    Returns:
        dict: The global configuration loaded from 'global_config.yaml'.
    """
    os.path.join(os.path.dirname(__file__), "global_config.yaml")
    with open("global_config.yaml", "r", encoding="utf-8") as config_file:
        config = yaml.load(config_file)

    return config


def get_config(private_folder: str) -> dict:
    """
    Prompts the user to select a configuration file from the specified private folder,
    loads the selected configuration file, and returns its contents as a dictionary.

    Args:
        private_folder (str): The path to the folder containing the configuration files.

    Returns:
        dict: The contents of the selected configuration file.
    """
    file_path = ""

    # Get the config file to use
    answer = input(
        "[Question] - Which config file would you like to use ? [config.yaml] "
    )
    if answer == "":
        answer = "config.yaml"

    # Load the config file
    file_path = os.path.join(private_folder, answer)
    with open(file_path, "r", encoding="utf-8") as config_file:
        config = yaml.load(config_file)

    return config


def recover_people(private_folder: str, config_sublist: str) -> list:
    """
    Recover people from a given input file, return it as a list of tuples.

    Args:
        private_folder (str): The path to the private folder containing the input
                              and output files.
        config_sublist (str): The sublist to take configuration from.

    Returns:
        list: A list of tuples, where each tuple contains the name and additional
              information of a person.
    """
    # Get the input file to use
    input_sublist = ""
    current_year = datetime.now().year
    input_file = os.path.join(private_folder, config_sublist, "input_mail_list.yaml")

    if config_sublist == "test_config":
        input_sublist = "test_config"
    else:
        input_sublist = f"year_{current_year}"

    # Recover peoples from file
    with open(input_file, "r", encoding="utf-8") as info:
        dict_info_people = yaml.load(info)[input_sublist]

    if not dict_info_people:
        print("[ERROR] - List of people is empty.")
        return []

    return list(dict_info_people.items())


def save_people(list_people: list, output_file: str):
    """
    Save the list of people into the output file.

    Args:
        list_people (list): A list of tuples, where each tuple contains the name
                            and additional information of a person.
        output_file (str): The path to the output file where the list of people
                           will be saved.
    """
    current_year = datetime.now().year

    # Load the existing data from the YAML file
    try:
        with open(output_file, "r", encoding="utf-8") as file:
            # Load existing data or initialize as empty dict if file is empty
            data = yaml.load(file) or {}
    except FileNotFoundError:
        data = {}  # Start with an empty dict if the file doesn't exist

    # Add the new entry to the data
    new_entry = {f"year_{current_year}": dict(list_people)}
    data.update(new_entry)

    # Dump the data to a string
    stream = StringIO()
    yaml.dump(data, stream)
    yaml_str = stream.getvalue()

    # Insert empty lines between sections
    sections = yaml_str.split("\n")
    formatted_sections = []

    for section in sections:
        if section == "":
            continue

        if re.compile(r"^[a-zA-Z0-9_-]+:").match(section):
            formatted_sections.append("\n")

        formatted_sections.append(section + "\n")
    formatted_yaml_str = "".join(formatted_sections).strip()

    # Write the formatted string back to the YAML file
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(formatted_yaml_str)


def create_body(recipient: str, target: str, mail_body: str) -> str:
    """
    Replaces placeholders in the mail body with the recipient and target names.

    Args:
        recipient (str): The name of the recipient.
        target (str): The name of the target.
        mail_body (str): The body of the mail containing placeholders.

    Returns:
        str: The mail body with placeholders replaced by the recipient and target names.
    """
    mail_body = mail_body.replace("CFG_RECIPIENT", recipient)
    mail_body = mail_body.replace("CFG_TARGET", target)

    return mail_body


def prompt_for_password() -> str:
    """
    Prompts the user for a password securely.

    Returns:
        str: The password entered by the user.
    """
    return getpass.getpass("[Question] - Type your password and press enter: ")


def send_email(body: str, password: str, smtp_server: str, port: int, **mail: dict):
    """
    Sends an email using the specified SMTP server and port.

    Args:
        body (str): The body of the email.
        password (str): The password for the sender's email account.
        smtp_server (str): The SMTP server address.
        port (int): The port to use for the SMTP server.
        mail (dict): A dictionary containing the email parameters.
    """
    # Create a text/plain message
    msg = MIMEMultipart()
    msg.attach(MIMEText(body, "plain"))

    # Set email parameters
    msg["Subject"] = mail.get("subject")
    msg["From"] = mail.get("sender")
    msg["To"] = mail.get("recipient")

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(mail["sender"], password)
        text = msg.as_string()
        server.sendmail(mail["subject"], mail["recipient"], text)


if __name__ == "__main__":
    main()
