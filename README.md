Generate Account and Vendor files using SadielCodingExercise App
===========================================================

This Python application allows the user to connect to SadielCodingExercise Xero App using the PyXero SDK.
It also generates account and vendor files selecting an organisation.


## 1. Configuration

Create `config.ini` file from `config.ini.example` and set `Consumer Key` and `Consumer Secret` OAuth 1.0a credentials.

## 2. Build `sadielexercise` image and run container

Run:

    docker build -t sadielexercise . && docker run -d -p 8000:8000 -v $(pwd)/accounts_and_vendors:/accounts_and_vendors sadielexercise

## 3. Generate vendor and account files

* Then open your browser and go to http://localhost:8000/
* Click on Connect to Xero button.
* Login with Xero developer credentials.
* Select Organization in the dropdown (Default: Demo company (Global)).
* Click Allow access for 30 mins button.
* The `vendors.js` and `accounts.js` files are gonna be generated in `../accounts_and_vendors` folder according to `config.ini` file.