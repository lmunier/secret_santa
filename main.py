#!/bin/usr/python3
# -*-coding:Utf-8 -*

"""
main.py

Author: Munier Louis
Version: 2.0
Date: 2024-11-08

Script to shuffle, send e-mail and generate PDF in the case of a friendly
secret santa. It gets the list of people from a file, shuffles it, saves it
to a file, and sends mail to each person. It also keeps information from
previous years, to avoid sending mail to the same person each time, and can
get pairs to avoid.
"""

import os
import sys
import re
import getpass
import random
import smtplib
import ssl
import socket
import logging

from io import StringIO
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from itertools import permutations
from ruamel.yaml import YAML
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Constants
CONFIG_FILE = "global_config.yaml"
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_SUBLIST = "test_config"

MAX_ITERATION = 1000
FONT_SIZE_TITLE = 24
FONT_SIZE_TEXT = 15

yaml = YAML()
yaml.preserve_quotes = True

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """Main function of the script."""
    global_config = get_global_config()
    private_config = get_config(global_config["private_folder"])

    # Get peoples from file
    config_sublist = input(
        f"[Question] - Which yaml sublist to take ? [{DEFAULT_SUBLIST}] "
    )
    if config_sublist == "":
        config_sublist = DEFAULT_SUBLIST
    elif config_sublist not in private_config:
        logging.error("This sublist does not exist.")
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

    # Generate PDF
    output_pdf = os.path.join(global_config["private_folder"], config_sublist)
    generate_pdf(
        output_pdf, list_people, private_config[config_sublist]["mail_subject"]
    )

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
    config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
    with open(config_path, "r", encoding="utf-8") as config_file:
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
    answer = input(
        f"[Question] - Which config file would you like to use ? [{DEFAULT_CONFIG_FILE}] "
    )
    if answer == "":
        answer = DEFAULT_CONFIG_FILE

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
    input_file = os.path.join(private_folder, config_sublist, people_list)
    input_sublist = (
        config_sublist if config_sublist == DEFAULT_SUBLIST else f"year_{year}"
    )

    with open(input_file, "r", encoding="utf-8") as info:
        dict_info_people = yaml.load(info).get(input_sublist, {})

    if not dict_info_people:
        logging.error("List of people is empty.")
        return [], []

    unwanted_people = dict_info_people.pop("unwanted", {})
    return list(dict_info_people.items()), list(unwanted_people.items())


def compute_all_possibilities(
    private_folder: str, config_sublist: str, nb_years: int
) -> list:
    """
    Compute possible pairs from all the possibilities and removing unwanted ones:
    - Same as old ones
    - Same as unwanted ones

    Args:
        private_folder (str): The path to the private folder containing the input
                              and output files.
        config_sublist (str): The sublist to take configuration from.
        nb_years (int): The number of years to consider when shuffling the list.

    Returns:
        list: A list with all the possible pairs without keeping the ones from
              the X previous years and the unwanted ones.
    """
    list_people, list_unwanted = get_people(
        private_folder, "input_mail_list.yaml", config_sublist
    )
    names = [person[0] for person in list_people]
    all_pairs = list(permutations(names, 2))

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

        all_pairs = [pair for pair in all_pairs if pair not in old_pairs]

    unwanted_pairs = [
        (unwanted[0], target) for unwanted in list_unwanted for target in unwanted[1]
    ]
    all_pairs = [pair for pair in all_pairs if pair not in unwanted_pairs]

    return all_pairs


def get_santas_list(private_folder: str, config_sublist: str, nb_years: int) -> list:
    """
    Shuffle the list of people until no one has the same assigned person as
    for the last nb_years of years or someone classified as unwanted.

    Args:
        private_folder (str): The path to the private folder containing the input
                              and output files.
        config_sublist (str): The sublist to take configuration from.
        nb_years (int): The number of years to consider when shuffling the list.

    Returns:
        list: The shuffled list of people.
    """
    list_people = get_people(private_folder, "input_mail_list.yaml", config_sublist)[0]

    answer = input("[Question] - Would you like to shuffle list ? [y/N] ")
    if not answer.lower() == "y":
        return list_people

    possible_list = compute_all_possibilities(private_folder, config_sublist, nb_years)

    for _ in range(MAX_ITERATION):
        random.shuffle(possible_list)

        list_santas = []
        list_filtered = possible_list.copy()
        santa, next_santa = list_filtered[0]

        for _, _ in enumerate(list_people):
            list_santas.append(
                next((person for person in list_people if person[0] == santa), None)
            )
            list_filtered = [pair for pair in list_filtered if santa not in pair]

            santa = next_santa
            next_santa = next(
                (person[1] for person in list_filtered if person[0] == santa),
                None,
            )

            if not santa:
                break

        if len(list_santas) == len(list_people):
            return list_santas

    logging.error("Could not shuffle list with the current conditions.")
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

    try:
        with open(output_file, "r", encoding="utf-8") as file:
            data = yaml.load(file) or {}
    except FileNotFoundError:
        data = {}

    new_entry = {f"year_{current_year}": dict(list_people)}
    data.update(new_entry)

    stream = StringIO()
    yaml.dump(data, stream)
    yaml_str = stream.getvalue()

    sections = yaml_str.split("\n")
    formatted_sections = []

    for section in sections:
        if section == "":
            continue

        if re.compile(r"^[a-zA-Z0-9_-]+:").match(section):
            formatted_sections.append("\n")

        formatted_sections.append(section + "\n")
    formatted_yaml_str = "".join(formatted_sections).strip()

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
    login = input("[Question] - Type your user mail login and press enter: ")
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
        logging.error(
            "Authentication error. Please check your credentials and try again."
        )
        return False
    except socket.timeout:
        logging.error(
            "Connection timed out. Please check your network connection and try again."
        )
        return False
    except socket.gaierror:
        logging.error(
            "Network error. Please check your internet connection and the SMTP server address."
        )
        return False
    except smtplib.SMTPException as error:
        logging.error("SMTP error occurred: %s", error)
        return False


def generate_pdf(file_path: str, list_people: list, title: str):
    """
    Create a simple PDF with the given text.

    Args:
        file_path (str): The path to save the PDF file.
        list_people (list): The generated list for the secret santa.
        title (str): Title of the generated pdf
    """
    pdf_title = title.replace(" ", "_")
    filename = os.path.join(file_path, f"{pdf_title}.pdf")

    output_pdf = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Write the title
    output_pdf.setFont("Helvetica-Bold", FONT_SIZE_TITLE)
    text_width = output_pdf.stringWidth(title, "Helvetica-Bold", FONT_SIZE_TITLE)
    x_position = (width - text_width) / 2
    y_position = height - FONT_SIZE_TITLE - 25
    output_pdf.drawString(x_position, y_position, title)

    # Add secret santa's list to the pdf
    arrow_unicode = "\u279F"
    output_pdf.setFont("Helvetica", FONT_SIZE_TEXT)

    for i in range(len(list_people) - 1):
        text = f"{list_people[i][0]} {arrow_unicode} {list_people[i + 1][0]}"
        output_pdf.drawString(100, height - (i + 1) * 1.5 * FONT_SIZE_TEXT - 100, text)

    output_pdf.save()


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
    param_mail_body = private_config[config_sublist]["mail_body"]
    login, password = get_credentials(
        private_config["timeout"], private_config["smtp_server"], private_config["port"]
    )

    for i, _ in enumerate(list_people):
        santa = list_people[i]
        santa_target = list_people[(i + 1) % len(list_people)]

        mail_body = param_mail_body.replace("CFG_RECIPIENT", santa[0])
        mail_body = mail_body.replace("CFG_TARGET", santa_target[0])

        msg = MIMEMultipart()
        msg.attach(MIMEText(mail_body, "plain"))

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
