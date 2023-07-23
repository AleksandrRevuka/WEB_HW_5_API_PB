import platform

import click
import aiohttp
import asyncio
import sys

from datetime import datetime, timedelta
from prettytable import PrettyTable

BASE_PAIRS = ["USD", "EUR"]


async def get_data(session, date):
    """
    The get_data function is an asynchronous function that takes in a session and date as parameters.
    It then uses the async with statement to make a GET request to the PrivatBank API using the provided date.
    If response is ok, it returns result which is await response.json()

    :param session: Pass the session object to the function
    :param date: Specify the date for which we want to get exchange rates
    :return: A dictionary with the following structure:
    """
    url = f"https://api.privatbank.ua/p24api/exchange_rates?json&date={date}"
    try:
        async with session.get(url) as response:
            if response.ok:
                result = await response.json()
                return result

    except aiohttp.ClientConnectorError as err:
        click.secho(f"Connection error: {url}", str(err), fg="red")


def make_table(data: list, pairs: list) -> str:
    """
    The make_table function takes two arguments:
        1. data - a list of dictionaries, each dictionary containing the following keys:
            * date - a string representing the date in YYYY-MM-DD format;
            * baseCurrencyLit - a string representing the currency code for which all other currencies are compared to;
            * exchangeRate - another list of dictionaries, each dictionary containing information about one currency pair
            and having these keys:
                + currency (string) — код валюты (например USD);

    :param data: list: Pass the data from the get_data function
    :param pairs: list: Add the pairs to the table
    :return: A string with a table of currency rates for the specified period
    """

    table = PrettyTable()
    table.field_names = ["Date", "Pair", "Bay", "Sell"]

    prev_date = None

    for data_day in data:
        date_for_table = data_day["date"]
        print_pairs = BASE_PAIRS + pairs

        for pair in print_pairs:
            pair_for_table = pair + "/" + data_day["baseCurrencyLit"]
            for data_pair in data_day["exchangeRate"]:
                if data_pair["currency"] == pair:
                    bay_pair = data_pair.get("purchaseRate") if data_pair.get("purchaseRate") else data_pair.get("purchaseRateNB")
                    sell_pair = data_pair.get("saleRate") if data_pair.get("saleRate") else data_pair.get("saleRateNB")

            if date_for_table != prev_date:
                prev_date = date_for_table
            else:
                date_for_table = ""
            table.add_row([date_for_table, pair_for_table, bay_pair, sell_pair])

    return str(table)


def print_exchange_rates(data: list, pairs=[]) -> None:
    """
    The print_exchange_rates function prints the exchange rates in a table.
        Args:
            data (dict): The dictionary containing the exchange rates.
            pairs (list): A list of currency pairs to print, if empty all are printed.

    :param data: Pass the data from the get_exchange_rates function to print out
    :param pairs: Specify which pairs to print
    :return: A table of exchange rates
    """

    if pairs:
        table = make_table(data, pairs)
        click.secho(f"{table}", fg="green")
    else:
        table = make_table(data, pairs)
        click.secho(f"{table}", fg="yellow")


def make_date_period(days: int) -> list[str]:
    """
    The make_date_period function takes a string of days as an argument and returns a list of dates in the format DD.MM.YYYY
        for the last X number of days, where X is equal to the number passed into make_date_period.

    :param days: str: Define the number of days from today's date to be included in the list
    """

    currency_date = datetime.now()

    date_period = [(currency_date - timedelta(days=i)).strftime("%d.%m.%Y") for i in range(days)]
    return date_period


async def run_get_data(period: list) -> list:
    """
    The run_get_data function is an asynchronous function that takes a list of dates as input.
    It then creates a session with the API and makes requests for each date in the list,
    returning all results at once.

    :param period: Specify the range of dates to retrieve data for
    :return: A list of lists
    """

    async with aiohttp.ClientSession() as session:
        tasks = []
        for date in period:
            task = asyncio.create_task(get_data(session, date))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results


def make_existing_pairs(data: list) -> list:
    """
    The make_existing_pairs function takes a list of dictionaries as an argument.
    It returns a list of currency pairs that are available for trading on the exchange.

    :param data: list: Store the data from the api
    :return: A list of all the currency pairs that are already in the database
    """

    return [data_pair["currency"] for data_pair in data[0]["exchangeRate"]]


@click.command(help="Console utility for viewing USD/UAH to EUR/UAH exchange rates for the last N days.")
@click.option("--pair", "-p", help="Show currency rate by code (example: 'plz,XAU,gbp').")
@click.argument("days", type=int)
def main(days: int, pair: str) -> None:
    """
    The main function is the entry point for this console utility.
    It takes two arguments: days and pair.
    The first argument is a number of days to show exchange rates for,
    the second one is an optional currency pair (USD/UAH or EUR/UAH) to show exchange rates for.

    :param days: str: Validate the number of days
    :param pair: str: Specify the currency pair
    :return: None
    """
    if days <= 0 or days > 10:
        click.secho("Incorrect number of days. Valid values are from 1 to 10.", fg="red")
        sys.exit()

    date_period = make_date_period(days)

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    data = asyncio.run(run_get_data(date_period))

    existing_pairs = [pair for pair in make_existing_pairs(data) if pair not in BASE_PAIRS]

    if pair:
        added_pairs = [pair.upper() for pair in pair.split(",") if pair.upper() in existing_pairs]
        print_exchange_rates(data, added_pairs)
    else:
        print_exchange_rates(data)


if __name__ == "__main__":
    main()
