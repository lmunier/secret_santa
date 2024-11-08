#!/bin/usr/python3
# -*-coding:Utf-8 -*

"""
main.py

Author: Munier Louis
Version: 1.2
Date: 2024-11-08

Script to shuffle and send e-mail in the case of a friendly secret santa.
It gets the list of people from a file, shuffles it, saves it to a file, and
sends mail to each person. It also keeps information from previous years to
avoid sending mail to the same person each time.
"""

import os
import sys
import re
import getpass
import random
import smtplib
import ssl
import socket

from io import StringIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from itertools import permutations
from ruamel.yaml import YAML


yaml = YAML()
yaml.preserve_quotes = True


def main():
    """Main function of the script."""
    list_people = []

    global_config = get_global_config()
    private_config = get_config(global_config["private_folder"])

    # Get peoples from file
    config_sublist = input("[Question] - Which yaml sublist to take ? [test_config] ")
    if config_sublist == "":
        config_sublist = "test_config"
    elif config_sublist not in private_config:
        print("[ERROR] - This sublist does not exist.")
        return

    # Get the list of people shuffled
    list_people = get_santas_list(
        global_config["private_folder"],
        config_sublist,
        private_config["year_before_repeat"],
    )

    # Save people order
    output_file = os.path.join(
        global_config["private_folder"], config_sublist, "output_mail_list.yaml"
    )
    save_people(list_people, output_file)

    # Send mail
    answer = input("[Question] - Would you like to send mail ? [y/N] ")
    if answer.lower() == "y":
        send_email(list_people, private_config, config_sublist)


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


def get_people(
    private_folder: str,
    people_list: str,
    config_sublist: str,
    year: str = datetime.now().year,
) -> tuple:
    """
    Get people from a given input file, return it as a list of tuples.

    Args:
        private_folder (str): The path to the private folder containing the input
                              and output files.
        people_list (str): The name of the file containing the list of people.
        config_sublist (str): The sublist to take configuration from.
        year (str): The year to use for the sublist.

    Returns:
        list: A list of tuples, where each tuple contains the name and additional
              information of a person.
    """
    # Get the input file to use
    input_sublist = ""
    input_file = os.path.join(private_folder, config_sublist, people_list)

    if config_sublist == "test_config":
        input_sublist = "test_config"
    else:
        input_sublist = f"year_{year}"

    # Get peoples from file
    with open(input_file, "r", encoding="utf-8") as info:
        dict_info_people = yaml.load(info)[input_sublist]

    if not dict_info_people:
        print("[ERROR] - List of people is empty.")
        return [], []

    if "unwanted" in dict_info_people:
        # Split the list of people into wanted and unwanted people
        unwanted_people = list(dict_info_people["unwanted"].items())
        dict_info_people.pop("unwanted")

        return list(dict_info_people.items()), unwanted_people

    return list(dict_info_people.items()), []


def compute_all_possibilities(
    private_folder: str, config_sublist: str, nb_years: int
) -> list:
    """
    Compute possible pairs from all the possibilities and removing unwanted ones:
    - Same as old ones
    - Same as unwanted ones

    Args:
        list_people (list): A list of tuples, where each tuple contains the name
                            and additional information of a person.

    Returns:
        list: A list with all the possible pairs without keeping the ones from
              the X previous years and the unwanted ones.
    """
    # Extract names from the list of tuples and generate all the possible pairs
    list_people, list_unwanted = get_people(
        private_folder, "input_mail_list.yaml", config_sublist
    )

    names = [person[0] for person in list_people]
    all_pairs = list(permutations(names, 2))

    # Get all the pairs from X previous years
    current_year = datetime.now().year
    for i in range(nb_years):
        old_list_people, _ = get_people(
            private_folder,
            "output_mail_list.yaml",
            config_sublist,
            year=current_year - i - 1,
        )

        old_pairs = [
            (old_list_people[i][0], old_list_people[(i + 1) % len(old_list_people)][0])
            for i, _ in enumerate(old_list_people)
        ]

        # Remove the pairs from the old list
        all_pairs = [pair for pair in all_pairs if pair not in old_pairs]

    # Remove the unwanted pairs
    unwanted_pairs = []
    for unwanted in list_unwanted:
        for unwanted_target in unwanted[1]:
            unwanted_pairs.append((unwanted[0], unwanted_target))

    all_pairs = [pair for pair in all_pairs if pair not in unwanted_pairs]

    return all_pairs


def get_santas_list(private_folder: str, config_sublist: str, nb_years: int) -> list:
    """
    Shuffle the list of people until no one has the same assigned person as
    for the last nb_years of yeas.

    Args:
        private_folder (str): The path to the private folder containing the input
                              and output files.
        config_sublist (str): The sublist to take configuration from.
        nb_years (int): The number of years to consider when shuffling the list.

    Returns:
        list: The shuffled list of people.
    """
    max_iteration = 1000
    list_people = get_people(private_folder, "input_mail_list.yaml", config_sublist)[0]

    # Shuffle list if and get all possibiles pairs based on criterias from the config files
    answer = input("[Question] - Would you like to shuffle list ? [y/N] ")
    if not answer.lower() == "y":
        return list_people

    possible_list = compute_all_possibilities(private_folder, config_sublist, nb_years)

    # Extract santas from the list of tuples
    list_santas = []
    random.shuffle(possible_list)

    first_run = True
    iteration = 0
    while iteration < max_iteration:
        while len(list_santas) < len(list_people) and possible_list:
            if first_run:
                santa = possible_list[0][0]
                next_santa = possible_list[0][1]
                first_run = False
            else:
                santa = next_santa

                try:
                    next_santa = next(
                        (pair[1] for pair in possible_list if pair[0] == santa)
                    )
                except StopIteration:
                    break

            list_santas.append(
                next((person for person in list_people if person[0] == santa), None)
            )

            # Remove all the pairs beginning with the current santa
            possible_list = [pair for pair in possible_list if santa not in pair]

            if len(list_santas) == len(list_people) - 1:
                list_santas.append(
                    next(
                        (person for person in list_people if person[0] == next_santa),
                        None,
                    )
                )

        if len(list_santas) == len(list_people):
            break

        first_run = True
        list_santas = []
        iteration += 1

    if len(list_santas) == len(list_people):
        return list_santas

    print("[ERROR] - Could not shuffle list with the current conditions.")
    sys.exit(1)


def save_people(list_people: list, output_file: str):
    """
    Save the list of people into the output file in a certain yaml format.

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


def get_credentials(timeout: int, smtp_server: str, port: int) -> tuple:
    """
    Prompts the user for email and password securely.

    Args:
        timeout (int): The timeout to use for the SMTP connection.
        smtp_server (str): The SMTP server address.
        port (int): The port to use for the SMTP server.

    Returns:
        tuple: The email and password entered by the user.
    """
    login = ""
    password = ""

    login = input("[Question] - Type your user mail login and press enter: ")

    # Get password securely
    password = getpass.getpass("[Question] - Type your password and press enter: ")

    if not check_credentials(timeout, smtp_server, port, login, password):
        return get_credentials(timeout, smtp_server, port)

    return login, password


def check_credentials(
    timeout: int, smtp_server: str, port: int, login: str, password: str
) -> bool:
    """
    Checks if the provided login and password are valid by attempting to log in to the SMTP server.

    Args:
        timeout (int): The timeout to use for the SMTP connection.
        smtp_server (str): The SMTP server address.
        port (int): The port to use for the SMTP server.
        login (str): The login to log in with.
        password (str): The password to log in with.

    Returns:
        bool: True if the credentials are valid, False otherwise.
    """
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(
            smtp_server, port, context=context, timeout=timeout
        ) as server:
            server.login(login, password)
        return True
    except smtplib.SMTPAuthenticationError:
        print(
            "[Error] - Authentication error. Please check your credentials and try again."
        )
        return False
    except socket.timeout:
        print(
            "[Error] - Connection timed out. Please check your network connection and try again."
        )
        return False
    except socket.gaierror:
        print(
            """[Error] - Network error. Please check your internet connection and the SMTP server
            address."""
        )
        return False
    except smtplib.SMTPException as error:
        print(f"[Error] - SMTP error occurred: {error}")
        return False


def send_email(list_people: list, private_config: dict, config_sublist: str):
    """
    Sends an email using the specified SMTP server and port.

    Args:
        list_people (list): A list of tuples, where each tuple contains the name
                            and additional information of a person.
        private_config (dict): The private configuration loaded from the private
                               configuration file.
        config_sublist (str): The sublist to take configuration from.
    """
    # Retrieve mail parameters
    param_mail_body = private_config[config_sublist]["mail_body"]

    # Prompt for email and password until valid credentials are provided
    login, password = get_credentials(
        private_config["timeout"], private_config["smtp_server"], private_config["port"]
    )

    # Send mail to each person
    for i, _ in enumerate(list_people):
        santa = list_people[i]
        santa_target = list_people[(i + 1) % len(list_people)]

        # Modify mail body
        mail_body = param_mail_body.replace("CFG_RECIPIENT", santa[0])
        mail_body = mail_body.replace("CFG_TARGET", santa_target[0])

        # Create a text/plain message
        msg = MIMEMultipart()
        msg.attach(MIMEText(mail_body, "plain"))

        # Set email parameters
        msg["Subject"] = private_config[config_sublist]["mail_subject"]
        msg["From"] = private_config["mail_sender"]
        msg["To"] = santa[1]

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            private_config["smtp_server"], private_config["port"], context=context
        ) as server:
            server.login(login, password)
            server.sendmail(private_config["mail_sender"], santa[1], msg.as_string())


if __name__ == "__main__":
    main()
