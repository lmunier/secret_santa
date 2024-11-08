# Overview

Here is a small project to send e-mails for a friendly Secret Santa. It is working in python3 and use a personnal e-mail and password to send them. Have a look to [Credits](#credits) to see the repos who made it possible.

## Getting Started

Begin by cloning this repository using :

```bash
git clone git@github.com:lmunier/secret_santa.git
```

## Assuming you already have python3 installed

**Recommended** - Source the virtual environment using :

```bash
source venv/bin/activate
```

**Not Recommended** - Installing python packages :

```bash
pip install -r requirements.txt
```

### Run

Then simply use python3 command to run *main.py* and follow the instructions. You have to fill the correct files to have a custom behavior, see the folder *example* to check all the files to modify.

## Usage

To use this project, modify the *global_config.yaml* file to include your private folder path. Take a look in the example folder to know the arborescence and what to put in your *config.yaml* file.

## Credits

This repo do use the library ruamel.yaml to manage YAML v1.2 files which is Licensing as MIT license : [ruamel](<https://github.com/commx/ruamel-yaml/tree/masters>)

It also use the library which is under BSD-3-Clause license [reportlab](<https://github.com/Distrotech/reportlab>)

## License

This work can be used under BSD-3-Clause License, see file LICENSE.

## Maintainers

- Louis Munier - <lmunier@protonmail.com>
