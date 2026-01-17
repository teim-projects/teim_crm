from dateutil.relativedelta import relativedelta


def generate_service_dates(start_date, end_date, frequency_months):
    """
    Generate planned AMC service dates between start and end date
    based on frequency (in months).
    """

    service_dates = []
    current_date = start_date

    while current_date <= end_date:
        service_dates.append(current_date)
        current_date = current_date + relativedelta(
            months=frequency_months
        )

    return service_dates
