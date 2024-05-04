from datetime import datetime


def convert_date_format(date_str) -> str:
    try:
        date_obj = datetime.strptime(date_str, "%d-%m-%Y %H:%M:%S")
    except ValueError:
        date_obj = datetime.strptime(date_str, "%d-%m-%Y")

    formatted_date = date_obj.strftime("%Y-%m-%d")

    return formatted_date
