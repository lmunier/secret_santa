#!/bin/usr/python3
# -*-coding:Utf-8 -*

# Name:     main.py
# Author:   Munier Louis
# Version:  1.2
# Date:     2024-11-05

# Script to shuffle and send e-mail in the case of a friendly secret santa.

import random
import smtplib
import ssl
import yaml

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def main():
    list_people = []
    current_year = datetime.now().year

    global_config = get_global_config()
    private_config = get_config(global_config["private_folder"])

    # Recover peoples from file
    answer = input("[Question] - Which yaml sublist to take ? [test] ")
    if answer == "":
        answer = "test"
    elif answer not in private_config:
        print("[ERROR] - This sublist does not exist.")
        return

    list_people = recover_people(private_config[answer]["input_file"])

    # Shuffle list if
    answer = input("[Question] - Would you like to shuffle list ? [y/N] ")
    if answer.lower() == "y":
        random.shuffle(list_people)

    # Save people to file
    yaml.add_representer(str, str_presenter)
    save_people(list_people, private_config["test"]["output_file"])

    # Send mail
    answer = input("[Question] - Would you like to send mail ? [y/N] ")
    if answer.lower() == "y":
        password = input("[Question] - Type your password and press enter: ")

        for n, people in enumerate(list_people):
            next_people = list_people[(n + 1) % len(list_people)][0]
            mail_body = create_body(people[0], next_people)

            send_email(
                private_config["mail_sender"],
                people[1],
                private_config["mail_subject"],
                mail_body,
                password,
                private_config["smtp_server"],
                private_config["port"],
            )


def get_global_config() -> dict:
    """
    Reads the global configuration from a YAML file and returns it as a dictionary.

    Returns:
        dict: The global configuration loaded from 'global_config.yaml'.
    """
    with open("global_config.yaml") as config_file:
        config = yaml.safe_load(config_file)

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
    file_path = private_folder + "/"

    # Get the config file to use
    answer = input(
        "[Question] - Which config file would you like to use ? [config.yaml] "
    )
    if answer == "":
        answer = "config.yaml"

    file_path += answer

    # Load the config file
    with open(file_path) as config_file:
        config = yaml.safe_load(config_file)

    return config


def recover_people(input_file: str) -> list:
    """
    Recover people from a given input file, optionally shuffle the list, and save to an output file.

    Args:
        input_file (str): The path to the input file containing the list of people.

    Returns:
        list: A list of tuples, where each tuple contains the name and additional information of a person.
    """
    # Recover peoples from file
    info_people = []
    with open(input_file, "r") as santas:
        for people in santas:
            people_split = people[:-1].split(",")
            info_people.append((people_split[0], people_split[1]))

    if len(info_people) == 0:
        print("[ERROR] - List of people is empty.")

    return info_people


def str_presenter(dumper: yaml.Dumper, data: str) -> yaml.Node:
    """
    Custom YAML string presenter for PyYAML.

    This function modifies the way strings are represented in YAML format.
    If the string contains a newline character, it will be represented using
    the block style (|). Otherwise, it will be represented using the default
    scalar style.

    Args:
        dumper (yaml.Dumper): The YAML dumper instance.
        data (str): The string data to be represented.

    Returns:
        yaml.Node: The YAML node representing the string.
    """
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")

    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def save_people(list_people: list, output_file: str):
    """
    Save the list of people into the output file.

    Args:
        list_people (list): A list of tuples, where each tuple contains the name and additional information of a person.
        output_file (str): The path to the output file where the list of people will be saved.
    """
    current_year = datetime.now().year

    # Load the existing data from the YAML file
    try:
        with open(output_file, "r") as file:
            # Load existing data or initialize as empty dict if file is empty
            data = yaml.safe_load(file) or {}
    except FileNotFoundError:
        data = {}  # Start with an empty dict if the file doesn't exist

    # Add the new entry to the data
    str_people = ""
    for people in list_people:
        str_people += f"{people[0]},{people[1]}\n"

    new_entry = {f"year_{current_year}": str_people}
    data.update(new_entry)

    # Write the updated data back to the YAML file
    with open(output_file, "w") as file:
        yaml.dump(data, file, default_flow_style=False)


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
    mail_body.replace("CFG_RECIPIENT", recipient)
    mail_body.replace("CFG_TARGET", target)

    return mail_body


def send_email(
    mail_sender: str,
    mail_recipient: str,
    mail_subject: str,
    body: str,
    password: str,
    smtp_server: str,
    port: int,
):
    """
    Sends an email using the specified SMTP server and port.

    Args:
        mail_sender (str): The email address of the sender.
        mail_recipient (str): The email address of the recipient.
        mail_subject (str): The subject of the email.
        body (str): The body of the email.
        password (str): The password for the sender's email account.
        smtp_server (str): The SMTP server address.
        port (int): The port to use for the SMTP server.
    """
    # Create a text/plain message
    msg = MIMEMultipart()
    msg.attach(MIMEText(body, "plain"))

    # Set email parameters
    msg["Subject"] = mail_subject
    msg["From"] = mail_sender
    msg["To"] = mail_recipient

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(mail_sender, password)
        text = msg.as_string()
        server.sendmail(mail_sender, mail_recipient, text)


if __name__ == "__main__":
    main()
